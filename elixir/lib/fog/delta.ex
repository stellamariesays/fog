defmodule Fog.Delta do
  @moduledoc """
  The change in fog between two FogMap snapshots.

  diff/2 is a pure function. Two maps in, one delta out.

  net < 0  → fog lifted (new signal entered the system)
  net ≈ 0  → epistemic arbitrage (ignorance redistributed, not reduced)
  net > 0  → fog deepened (agent knows less than before)
  """

  alias Fog.{Map, Gap}

  @type t :: %__MODULE__{
    agent_id:       String.t(),
    gaps_lifted:    MapSet.t(String.t()),
    gaps_added:     MapSet.t(String.t()),
    gaps_unchanged: MapSet.t(String.t()),
    before_map:     Map.t() | nil,
    after_map:      Map.t() | nil,
    half_life:      non_neg_integer()
  }

  defstruct [
    :agent_id, :gaps_lifted, :gaps_added, :gaps_unchanged,
    before_map: nil,
    after_map:  nil,
    half_life:  7 * 24 * 3600
  ]

  @eps 1.0e-9

  @doc "Compute the fog delta between two map snapshots."
  def diff(%Map{} = before, %Map{} = after_map, half_life \\ 7 * 24 * 3600) do
    before_keys = before.gaps    |> Elixir.Map.keys() |> MapSet.new()
    after_keys  = after_map.gaps |> Elixir.Map.keys() |> MapSet.new()

    %__MODULE__{
      agent_id:       before.agent_id,
      gaps_lifted:    MapSet.difference(before_keys, after_keys),
      gaps_added:     MapSet.difference(after_keys, before_keys),
      gaps_unchanged: MapSet.intersection(before_keys, after_keys),
      before_map:     before,
      after_map:      after_map,
      half_life:      half_life
    }
  end

  @doc """
  Weighted net change in fog volume.
      net = vol(added) − vol(lifted)

  Uses effective_confidence as weights.
  Falls back to raw counts when map refs are unavailable.
  """
  def net(%__MODULE__{before_map: nil} = delta) do
    MapSet.size(delta.gaps_added) - MapSet.size(delta.gaps_lifted)
  end

  def net(%__MODULE__{} = delta) do
    hl = delta.half_life

    vol_added =
      delta.gaps_added
      |> MapSet.to_list()
      |> Enum.reduce(0.0, fn k, acc ->
           case Elixir.Map.get(delta.after_map.gaps, k) do
             nil -> acc
             gap -> acc + Gap.effective_confidence(gap, hl)
           end
         end)

    vol_lifted =
      delta.gaps_lifted
      |> MapSet.to_list()
      |> Enum.reduce(0.0, fn k, acc ->
           case Elixir.Map.get(delta.before_map.gaps, k) do
             nil -> acc
             gap -> acc + Gap.effective_confidence(gap, hl)
           end
         end)

    vol_added - vol_lifted
  end

  @doc """
  Change in fog entropy between before and after.
      ΔH = H(after) − H(before)

  ΔH < 0: fog became more concentrated.
  ΔH > 0: fog spread out — broader, more diffuse uncertainty.
  ΔH ≈ 0: same structural shape of ignorance.
  """
  def entropy_delta(%__MODULE__{before_map: nil}), do: :undefined
  def entropy_delta(%__MODULE__{} = delta) do
    hl = delta.half_life
    Fog.Map.entropy(delta.after_map, hl) - Fog.Map.entropy(delta.before_map, hl)
  end

  @doc "True if fog moved but didn't shrink — ignorance redistributed, not reduced."
  def arbitrage?(%__MODULE__{} = delta) do
    MapSet.size(delta.gaps_lifted) > 0 and abs(net(delta)) < @eps
  end

  @doc "True if fog genuinely shrank — new signal entered."
  def lift?(%__MODULE__{} = delta), do: net(delta) < -@eps

  @doc "True if the agent knows less than before."
  def deepening?(%__MODULE__{} = delta), do: net(delta) > @eps

  @doc "Human-readable summary."
  def summary(%__MODULE__{} = delta) do
    n  = net(delta)
    ed = entropy_delta(delta)
    ed_str = if ed != :undefined, do: " ΔH=#{Float.round(ed, 3)}", else: ""

    cond do
      abs(n) < @eps and MapSet.size(delta.gaps_lifted) == 0 ->
        "[#{delta.agent_id}] static — no change#{ed_str}"
      arbitrage?(delta) ->
        "[#{delta.agent_id}] arbitrage — " <>
        "+#{MapSet.size(delta.gaps_added)} -#{MapSet.size(delta.gaps_lifted)} " <>
        "net=#{Float.round(n, 3)} (ignorance redistributed)#{ed_str}"
      lift?(delta) ->
        "[#{delta.agent_id}] lift — net=#{Float.round(n, 3)} (fog clearing)#{ed_str}"
      true ->
        "[#{delta.agent_id}] deepening — net=+#{Float.round(n, 3)}#{ed_str}"
    end
  end
end
