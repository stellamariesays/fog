defmodule Fog.Detect.Arbitrage do
  @moduledoc """
  Detect epistemic arbitrage across a mesh of agents.

  Arbitrage: ignorance is moving but not shrinking.
  The system looks more informed. The total dark is unchanged.
  """

  alias Fog.Delta

  @doc """
  Given a list of {before, after} FogMap pairs, return deltas
  flagged as epistemic arbitrage.
  """
  def detect(snapshots) do
    snapshots
    |> Enum.map(fn {before, after_map} -> Delta.diff(before, after_map) end)
    |> Enum.filter(&Delta.arbitrage?/1)
  end

  @doc """
  Net change in total system ignorance across all agents.

  Negative = fog actually lifted (new signal entered).
  Zero     = pure redistribution (epistemic arbitrage).
  Positive = system knows less than before.
  """
  def system_fog_change(snapshots) do
    snapshots
    |> Enum.map(fn {before, after_map} -> Delta.diff(before, after_map) |> Delta.net() end)
    |> Enum.sum()
  end
end
