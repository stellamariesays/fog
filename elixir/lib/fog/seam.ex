defmodule Fog.Seam do
  @moduledoc """
  Boundary between two agents' fog maps.

  High tension → agents have different blind spots → transfer potential.
  Zero tension → same fog everywhere → pure arbitrage territory.

  measure/2 is a pure function. Two maps in, one seam out.
  Pipe it:

      fog_a
      |> then(fn a -> Fog.Seam.measure(a, fog_b) end)
      |> Fog.Seam.summary()
  """

  alias Fog.{Map, Gap}

  @type t :: %__MODULE__{
    agent_a:    String.t(),
    agent_b:    String.t(),
    only_in_a:  MapSet.t(String.t()),
    only_in_b:  MapSet.t(String.t()),
    shared:     MapSet.t(String.t()),
    map_a:      Map.t() | nil,
    map_b:      Map.t() | nil,
    half_life:  non_neg_integer()
  }

  defstruct [
    :agent_a, :agent_b, :only_in_a, :only_in_b, :shared,
    map_a:    nil,
    map_b:    nil,
    half_life: 7 * 24 * 3600
  ]

  @smooth 1.0e-9  # epsilon for KL where a gap is absent

  @doc "Measure the seam between two agents' fog maps."
  def measure(%Map{} = map_a, %Map{} = map_b, half_life \\ 7 * 24 * 3600) do
    a_keys = map_a.gaps |> Elixir.Map.keys() |> MapSet.new()
    b_keys = map_b.gaps |> Elixir.Map.keys() |> MapSet.new()

    %__MODULE__{
      agent_a:   map_a.agent_id,
      agent_b:   map_b.agent_id,
      only_in_a: MapSet.difference(a_keys, b_keys),
      only_in_b: MapSet.difference(b_keys, a_keys),
      shared:    MapSet.intersection(a_keys, b_keys),
      map_a:     map_a,
      map_b:     map_b,
      half_life: half_life
    }
  end

  @doc """
  Weighted seam tension: fraction of total fog volume that is asymmetric.

      tension = vol(A-only ∪ B-only) / vol(A ∪ B)

  Uses effective_confidence as weights. Falls back to unweighted counts
  when map refs are unavailable.

  1.0 = perfectly asymmetric blind spots (maximum transfer potential)
  0.0 = identical fog on both sides (pure arbitrage territory)
  """
  def tension(%__MODULE__{map_a: nil} = seam) do
    total = MapSet.size(seam.only_in_a) + MapSet.size(seam.only_in_b) + MapSet.size(seam.shared)
    case total do
      0 -> 0.0
      _ -> (MapSet.size(seam.only_in_a) + MapSet.size(seam.only_in_b)) / total
    end
  end

  def tension(%__MODULE__{} = seam) do
    hl = seam.half_life

    eff = fn fmap, keys ->
      keys
      |> MapSet.to_list()
      |> Enum.reduce(0.0, fn k, acc ->
           case Elixir.Map.get(fmap.gaps, k) do
             nil -> acc
             gap -> acc + Gap.effective_confidence(gap, hl)
           end
         end)
    end

    vol_asym =
      eff.(seam.map_a, seam.only_in_a) + eff.(seam.map_b, seam.only_in_b)

    vol_shared =
      seam.shared
      |> MapSet.to_list()
      |> Enum.reduce(0.0, fn k, acc ->
           ea = case Elixir.Map.get(seam.map_a.gaps, k) do
                  nil -> 0.0; gap -> Gap.effective_confidence(gap, hl) end
           eb = case Elixir.Map.get(seam.map_b.gaps, k) do
                  nil -> 0.0; gap -> Gap.effective_confidence(gap, hl) end
           acc + max(ea, eb)
         end)

    total = vol_asym + vol_shared
    if total > 0, do: vol_asym / total, else: 0.0
  end

  @doc """
  KL divergence between the two fog distributions.
      D_KL(A ∥ B) = Σ p_A(x) log(p_A(x) / p_B(x))

  direction: :a_to_b (default) or :b_to_a
  Asymmetric — A→B ≠ B→A.
  """
  def kl_divergence(%__MODULE__{map_a: nil}, _direction), do: :undefined
  def kl_divergence(%__MODULE__{} = seam, direction \\ :a_to_b) do
    hl    = seam.half_life
    vol_a = Fog.Map.fog_volume(seam.map_a, hl)
    vol_b = Fog.Map.fog_volume(seam.map_b, hl)
    va    = if vol_a > 0, do: vol_a, else: 1.0
    vb    = if vol_b > 0, do: vol_b, else: 1.0

    universe = MapSet.union(
      seam.map_a.gaps |> Elixir.Map.keys() |> MapSet.new(),
      seam.map_b.gaps |> Elixir.Map.keys() |> MapSet.new()
    )

    pa = fn k ->
      case Elixir.Map.get(seam.map_a.gaps, k) do
        nil -> @smooth
        gap -> Gap.effective_confidence(gap, hl) / va
      end
    end

    pb = fn k ->
      case Elixir.Map.get(seam.map_b.gaps, k) do
        nil -> @smooth
        gap -> Gap.effective_confidence(gap, hl) / vb
      end
    end

    universe
    |> MapSet.to_list()
    |> Enum.reduce(0.0, fn k, acc ->
         {p, q} = if direction == :a_to_b, do: {pa.(k), pb.(k)}, else: {pb.(k), pa.(k)}
         acc + p * :math.log(p / q)
       end)
  end

  @doc """
  Jensen-Shannon divergence — symmetric, bounded [0, 1] in bits.
      JS(A, B) = ½ D_KL(A ∥ M) + ½ D_KL(B ∥ M)  where M = (A + B) / 2

  0.0 = identical distributions
  1.0 = completely disjoint fog
  """
  def js_divergence(%__MODULE__{map_a: nil}), do: :undefined
  def js_divergence(%__MODULE__{} = seam) do
    hl    = seam.half_life
    vol_a = max(Fog.Map.fog_volume(seam.map_a, hl), 1.0e-9)
    vol_b = max(Fog.Map.fog_volume(seam.map_b, hl), 1.0e-9)

    universe = MapSet.union(
      seam.map_a.gaps |> Elixir.Map.keys() |> MapSet.new(),
      seam.map_b.gaps |> Elixir.Map.keys() |> MapSet.new()
    )

    pa = fn k ->
      case Elixir.Map.get(seam.map_a.gaps, k) do
        nil -> @smooth
        gap -> Gap.effective_confidence(gap, hl) / vol_a
      end
    end

    pb = fn k ->
      case Elixir.Map.get(seam.map_b.gaps, k) do
        nil -> @smooth
        gap -> Gap.effective_confidence(gap, hl) / vol_b
      end
    end

    kl2 = fn p, q -> if p > 0, do: p * :math.log2(p / q), else: 0.0 end

    universe
    |> MapSet.to_list()
    |> Enum.reduce(0.0, fn k, acc ->
         p = pa.(k); q = pb.(k); m = (p + q) / 2
         acc + 0.5 * kl2.(p, m) + 0.5 * kl2.(q, m)
       end)
  end

  @doc "Gaps neither agent can fill — need external signal."
  def system_gaps(%__MODULE__{} = seam), do: seam.shared

  @doc "Human-readable summary including KL and JS when available."
  def summary(%__MODULE__{} = seam) do
    t = Float.round(tension(seam), 3)
    base = "FogSeam(#{seam.agent_a}↔#{seam.agent_b}) " <>
           "tension=#{t} " <>
           "A-only=#{MapSet.size(seam.only_in_a)} " <>
           "B-only=#{MapSet.size(seam.only_in_b)} " <>
           "shared=#{MapSet.size(seam.shared)}"

    kl = kl_divergence(seam)
    js = js_divergence(seam)

    extras =
      [
        (if kl != :undefined, do: " KL(A→B)=#{Float.round(kl, 3)}", else: nil),
        (if js != :undefined, do: " JS=#{Float.round(js, 3)}", else: nil)
      ]
      |> Enum.reject(&is_nil/1)
      |> Enum.join()

    base <> extras
  end
end
