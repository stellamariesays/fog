defmodule Fog.Delta do
  @moduledoc """
  The change in fog between two FogMap snapshots.

  diff/2 is a pure function. Two maps in, one delta out.

  net < 0  → fog lifted (new signal entered the system)
  net == 0 → epistemic arbitrage (ignorance redistributed, not reduced)
  net > 0  → fog deepened (agent knows less than before)
  """

  alias Fog.Map, as: FogMap

  @type t :: %__MODULE__{
    agent_id:        String.t(),
    gaps_lifted:     MapSet.t(String.t()),
    gaps_added:      MapSet.t(String.t()),
    gaps_unchanged:  MapSet.t(String.t())
  }

  defstruct [:agent_id, :gaps_lifted, :gaps_added, :gaps_unchanged]

  @doc "Compute the fog delta between two map snapshots."
  def diff(%FogMap{} = before, %FogMap{} = after) do
    before_keys = before.gaps |> Map.keys() |> MapSet.new()
    after_keys  = after.gaps  |> Map.keys() |> MapSet.new()

    %__MODULE__{
      agent_id:       before.agent_id,
      gaps_lifted:    MapSet.difference(before_keys, after_keys),
      gaps_added:     MapSet.difference(after_keys, before_keys),
      gaps_unchanged: MapSet.intersection(before_keys, after_keys)
    }
  end

  @doc "Net change in fog. Negative is good."
  def net(%__MODULE__{} = delta) do
    MapSet.size(delta.gaps_added) - MapSet.size(delta.gaps_lifted)
  end

  @doc "True if fog moved but didn't shrink — ignorance redistributed, not reduced."
  def arbitrage?(%__MODULE__{} = delta) do
    MapSet.size(delta.gaps_lifted) > 0 and net(delta) == 0
  end

  @doc "True if fog genuinely shrank — new signal entered."
  def lift?(%__MODULE__{} = delta), do: net(delta) < 0

  @doc "True if the agent knows less than before."
  def deepening?(%__MODULE__{} = delta), do: net(delta) > 0

  @doc "Human-readable summary."
  def summary(%__MODULE__{} = delta) do
    n = net(delta)
    cond do
      n == 0 and MapSet.size(delta.gaps_lifted) == 0 ->
        "[#{delta.agent_id}] static — no change"
      arbitrage?(delta) ->
        "[#{delta.agent_id}] arbitrage — " <>
        "+#{MapSet.size(delta.gaps_added)} -#{MapSet.size(delta.gaps_lifted)} net=0 " <>
        "(ignorance redistributed, not reduced)"
      lift?(delta) ->
        "[#{delta.agent_id}] lift — net=#{n} (fog clearing)"
      true ->
        "[#{delta.agent_id}] deepening — net=+#{n}"
    end
  end
end
