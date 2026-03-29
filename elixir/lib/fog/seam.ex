defmodule Fog.Seam do
  @moduledoc """
  Boundary between two agents' fog maps.

  High tension → agents have different blind spots → transfer potential.
  Zero tension → same fog everywhere → pure arbitrage territory.

  measure/2 is a pure function. Two maps in, one seam out.
  Pipe it:

      agent_a
      |> Fog.Map.add("orbital-mechanics", :known_unknown)
      |> then(fn fog_a -> Fog.Seam.measure(fog_a, fog_b) end)
      |> Fog.Seam.summary()
  """

  alias Fog.Map, as: FogMap

  @type t :: %__MODULE__{
    agent_a:    String.t(),
    agent_b:    String.t(),
    only_in_a:  MapSet.t(String.t()),
    only_in_b:  MapSet.t(String.t()),
    shared:     MapSet.t(String.t())
  }

  defstruct [:agent_a, :agent_b, :only_in_a, :only_in_b, :shared]

  @doc "Measure the seam between two agents' fog maps."
  def measure(%FogMap{} = map_a, %FogMap{} = map_b) do
    a_keys = map_a.gaps |> Map.keys() |> MapSet.new()
    b_keys = map_b.gaps |> Map.keys() |> MapSet.new()

    %__MODULE__{
      agent_a:   map_a.agent_id,
      agent_b:   map_b.agent_id,
      only_in_a: MapSet.difference(a_keys, b_keys),
      only_in_b: MapSet.difference(b_keys, a_keys),
      shared:    MapSet.intersection(a_keys, b_keys)
    }
  end

  @doc """
  Seam tension: fraction of gaps that are asymmetric (0.0–1.0).
  High tension → different blind spots → transfer potential.
  """
  def tension(%__MODULE__{} = seam) do
    total = MapSet.size(seam.only_in_a) + MapSet.size(seam.only_in_b) + MapSet.size(seam.shared)
    case total do
      0 -> 0.0
      _ -> (MapSet.size(seam.only_in_a) + MapSet.size(seam.only_in_b)) / total
    end
  end

  @doc "Gaps neither agent can fill — need external signal."
  def system_gaps(%__MODULE__{} = seam), do: seam.shared

  @doc "Interpretation based on tension score."
  def interpretation(%__MODULE__{} = seam) do
    case tension(seam) do
      t when t > 0.7 -> "high-potential seam — asymmetric blind spots, strong transfer signal"
      t when t > 0.4 -> "active seam — partial overlap, exchange probable"
      t when t > 0.0 -> "low-tension seam — mostly shared fog, limited exchange value"
      _              -> "flat seam — identical fog, no transfer possible"
    end
  end

  @doc "Human-readable summary."
  def summary(%__MODULE__{} = seam) do
    t = Float.round(tension(seam), 2)
    "FogSeam(#{seam.agent_a}↔#{seam.agent_b}) " <>
    "tension=#{t} " <>
    "A-only=#{MapSet.size(seam.only_in_a)} " <>
    "B-only=#{MapSet.size(seam.only_in_b)} " <>
    "shared=#{MapSet.size(seam.shared)} " <>
    "— #{interpretation(seam)}"
  end
end
