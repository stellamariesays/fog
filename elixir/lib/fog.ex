defmodule Fog do
  @moduledoc """
  Epistemic fog mapping for agent meshes.

  Tracks what agents don't know — not what they do.

  ## Core concepts

  - **FogMap** — an agent's structured ignorance. Gaps weighted by confidence, decaying over time.
  - **FogSeam** — boundary between two agents' fog maps. Weighted tension + KL/JS divergence.
  - **FogDelta** — change in fog between snapshots. Weighted net + entropy delta.
  - **FogMesh** — multi-agent layer with propagation. Dark core detection. System entropy.

  ## Quick start

      alias Fog.{Map, Seam, Delta, Mesh}

      fog_a =
        Map.new("braid")
        |> Map.add("multi-star-prediction", :known_unknown, domain: "solar", confidence: 0.9)
        |> Map.add("coronal-mass-ejection", :inferred_unknown, domain: "mesh")

      fog_b =
        Map.new("solver")
        |> Map.add("flare-induced-correction", :known_unknown, domain: "orbital")

      seam = Seam.measure(fog_a, fog_b)
      IO.puts Seam.summary(seam)
      # FogSeam(braid↔solver) tension=0.947 A-only=2 B-only=1 shared=0
      # KL(A→B)=1.433 JS=0.918

      # Fog volume and entropy
      IO.puts Map.fog_volume(fog_a)    # effective mass of ignorance
      IO.puts Map.entropy(fog_a)       # how diffuse that ignorance is

      # Detect arbitrage
      {fog_a2, :lifted} = Map.remove(fog_a, "multi-star-prediction", "solar")
      fog_a3 = Map.add(fog_a2, "new-gap", :known_unknown)
      delta = Delta.diff(fog_a, fog_a3)
      IO.puts Delta.summary(delta)
      # [braid] arbitrage — +1 -1 net=0.0 (ignorance redistributed) ΔH=+0.042

      # Multi-agent mesh with propagation
      mesh =
        Mesh.new()
        |> Mesh.register(fog_a)
        |> Mesh.register(fog_b)

      IO.inspect Mesh.snapshot(mesh)
      # %{agents: 2, system_entropy: 1.585, dark_core: 0, ...}

      # Propagate: fog_a learns something — update inferred_unknowns in other agents
      {mesh2, updated} = Mesh.propagate_lift(mesh, "braid", "coronal-mass-ejection", "mesh")

  ## Stateful agent (wrap in GenServer)

      defmodule FogAgent do
        use GenServer
        def init(agent_id), do: {:ok, Fog.Map.new(agent_id)}
        def handle_call({:add, key, kind, opts}, _from, fog),
          do: {:reply, :ok, Fog.Map.add(fog, key, kind, opts)}
        def handle_call(:snapshot, _from, fog),
          do: {:reply, fog, fog}
      end
  """
end
