defmodule Fog.Detect.Arbitrage do
  @moduledoc """
  Detect epistemic arbitrage across a mesh of agents.

  Arbitrage: ignorance is moving but not shrinking.
  The system looks more informed. The total dark is conserved.
  """

  alias Fog.Delta

  @eps 1.0e-9

  @doc """
  Given a list of {before, after} FogMap pairs, return deltas
  flagged as epistemic arbitrage. Uses weighted net (effective_confidence).
  """
  def detect(snapshots, half_life \\ 7 * 24 * 3600) do
    snapshots
    |> Enum.map(fn {before, after_map} -> Delta.diff(before, after_map, half_life) end)
    |> Enum.filter(&Delta.arbitrage?/1)
  end

  @doc """
  Weighted net change in total system ignorance across all agents.
  Negative = fog actually lifted. Zero = redistribution. Positive = deeper.
  """
  def system_fog_change(snapshots, half_life \\ 7 * 24 * 3600) do
    snapshots
    |> Enum.map(fn {before, after_map} ->
         Delta.diff(before, after_map, half_life) |> Delta.net()
       end)
    |> Enum.sum()
  end

  @doc """
  Net change in total system entropy across all agents.
  Negative = fog structure became more concentrated system-wide.
  Zero     = same entropy shape (even with churn).
  Positive = broader, more diffuse uncertainty.
  """
  def system_entropy_change(snapshots, half_life \\ 7 * 24 * 3600) do
    snapshots
    |> Enum.map(fn {before, after_map} ->
         case Delta.diff(before, after_map, half_life) |> Delta.entropy_delta() do
           :undefined -> 0.0
           v          -> v
         end
       end)
    |> Enum.sum()
  end

  @doc """
  True if total system fog volume is conserved despite individual churn.
  This is the mesh-level dark conservation law.
  """
  def dark_conserved?(snapshots, half_life \\ 7 * 24 * 3600, tolerance \\ @eps) do
    abs(system_fog_change(snapshots, half_life)) < tolerance
  end
end
