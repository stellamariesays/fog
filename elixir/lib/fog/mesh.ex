defmodule Fog.Mesh do
  @moduledoc """
  Multi-agent fog layer with propagation.

  FogMesh is an immutable value — a map of agent_id → FogMap.
  Operations return new meshes (or lists of updated meshes).

  Propagation rule: when agent A lifts fog on key X, all other agents
  holding :inferred_unknown on X have their confidence halved — the
  topological inference that X is universally unknown no longer holds.

  The dark_core is what no internal propagation can touch — gaps present
  in every agent's map. External signal required to clear these.

  To use as a stateful process, wrap in a GenServer:

      defmodule FogMeshServer do
        use GenServer
        def init(half_life),                do: {:ok, Fog.Mesh.new(half_life)}
        def handle_call({:register, fog},   _, mesh), do: {:reply, :ok, Fog.Mesh.register(mesh, fog)}
        def handle_call(:snapshot,          _, mesh), do: {:reply, Fog.Mesh.snapshot(mesh), mesh}
        def handle_call({:propagate, a, k}, _, mesh) ->
          {mesh2, updated} = Fog.Mesh.propagate_lift(mesh, a, k)
          {:reply, updated, mesh2}
        end
      end
  """

  alias Fog.{Map, Gap, Seam}

  @type t :: %__MODULE__{
    agents:    %{String.t() => Map.t()},
    half_life: non_neg_integer()
  }

  defstruct agents: %{}, half_life: 7 * 24 * 3600

  @propagation_factor 0.5

  @doc "Create an empty mesh."
  def new(half_life \\ 7 * 24 * 3600) do
    %__MODULE__{half_life: half_life}
  end

  @doc "Register an agent's fog map. Returns updated mesh."
  def register(%__MODULE__{} = mesh, %Map{} = fog_map) do
    %{mesh | agents: Elixir.Map.put(mesh.agents, fog_map.agent_id, fog_map)}
  end

  @doc """
  Propagate a fog lift from agent_id on key across the mesh.

  For every other agent holding :inferred_unknown on the same key,
  multiply their confidence by the propagation factor (default 0.5).

  Returns {updated_mesh, [agent_ids that were updated]}.
  """
  def propagate_lift(%__MODULE__{} = mesh, agent_id, key, domain \\ nil,
                     factor \\ @propagation_factor) do
    full_key = if domain, do: "#{domain}:#{key}", else: key

    {updated_agents, touched} =
      mesh.agents
      |> Enum.reduce({mesh.agents, []}, fn {aid, fmap}, {agents_acc, touched_acc} ->
           if aid == agent_id do
             {agents_acc, touched_acc}
           else
             case Elixir.Map.get(fmap.gaps, full_key) do
               %Gap{kind: :inferred_unknown} = gap ->
                 new_gap   = %{gap | confidence: max(gap.confidence * factor, 0.0),
                                     last_seen: System.system_time(:second)}
                 new_fmap  = %{fmap | gaps: Elixir.Map.put(fmap.gaps, full_key, new_gap)}
                 {Elixir.Map.put(agents_acc, aid, new_fmap), [aid | touched_acc]}
               _ ->
                 {agents_acc, touched_acc}
             end
           end
         end)

    {%{mesh | agents: updated_agents}, Enum.reverse(touched)}
  end

  @doc "Sum of all effective confidences across all agents (not deduplicated)."
  def total_fog_volume(%__MODULE__{} = mesh) do
    mesh.agents
    |> Elixir.Map.values()
    |> Enum.reduce(0.0, &(Fog.Map.fog_volume(&1, mesh.half_life) + &2))
  end

  @doc """
  Deduplicated fog volume: each gap key counted once at max confidence.
  Measures actual system ignorance, not agent-redundant ignorance.
  """
  def system_fog_volume(%__MODULE__{} = mesh) do
    mesh.agents
    |> Elixir.Map.values()
    |> Enum.reduce(%{}, fn fmap, acc ->
         Enum.reduce(fmap.gaps, acc, fn {k, gap}, inner_acc ->
           eff = Gap.effective_confidence(gap, mesh.half_life)
           Elixir.Map.update(inner_acc, k, eff, &max(&1, eff))
         end)
       end)
    |> Elixir.Map.values()
    |> Enum.sum()
  end

  @doc """
  Shannon entropy of the total mesh fog distribution.
  Treats all gaps across all agents as a single flat distribution.
  """
  def system_entropy(%__MODULE__{} = mesh) do
    effs =
      mesh.agents
      |> Elixir.Map.values()
      |> Enum.flat_map(fn fmap ->
           Enum.map(fmap.gaps, fn {_, gap} -> Gap.effective_confidence(gap, mesh.half_life) end)
         end)

    total = Enum.sum(effs)
    if total == 0.0 do
      0.0
    else
      Enum.reduce(effs, 0.0, fn e, acc ->
        p = e / total
        if p > 0, do: acc - p * :math.log2(p), else: acc
      end)
    end
  end

  @doc "All gap keys present in any agent."
  def union_gaps(%__MODULE__{} = mesh) do
    mesh.agents
    |> Elixir.Map.values()
    |> Enum.reduce(MapSet.new(), fn fmap, acc ->
         MapSet.union(acc, fmap.gaps |> Elixir.Map.keys() |> MapSet.new())
       end)
  end

  @doc """
  Gaps present in ALL agents — genuine system-wide blind spots.
  No internal propagation can clear these. External signal required.
  """
  def dark_core(%__MODULE__{} = mesh) do
    case Elixir.Map.values(mesh.agents) do
      []    -> MapSet.new()
      fmaps ->
        fmaps
        |> Enum.map(fn fmap -> fmap.gaps |> Elixir.Map.keys() |> MapSet.new() end)
        |> Enum.reduce(&MapSet.intersection/2)
    end
  end

  @doc "All pairwise seams across the mesh."
  def seam_matrix(%__MODULE__{} = mesh) do
    agents = Elixir.Map.values(mesh.agents)

    for {a, i} <- Enum.with_index(agents),
        b      <- Enum.drop(agents, i + 1),
        into: %{} do
      {{a.agent_id, b.agent_id}, Seam.measure(a, b, mesh.half_life)}
    end
  end

  @doc "Which pair of agents has the most to offer each other?"
  def highest_tension_seam(%__MODULE__{} = mesh) do
    matrix = seam_matrix(mesh)
    if map_size(matrix) == 0 do
      nil
    else
      {_pair, seam} = Enum.max_by(matrix, fn {_, s} -> Seam.tension(s) end)
      seam
    end
  end

  @doc "Summary metrics for the current mesh state."
  def snapshot(%__MODULE__{} = mesh) do
    %{
      agents:         map_size(mesh.agents),
      total_volume:   Float.round(total_fog_volume(mesh), 3),
      system_volume:  Float.round(system_fog_volume(mesh), 3),
      system_entropy: Float.round(system_entropy(mesh), 3),
      union_gaps:     MapSet.size(union_gaps(mesh)),
      dark_core:      MapSet.size(dark_core(mesh))
    }
  end
end
