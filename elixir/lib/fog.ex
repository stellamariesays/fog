defmodule Fog do
  @moduledoc """
  Epistemic fog mapping for agent meshes.

  Tracks what agents don't know — not what they do.

  Quick start:

      alias Fog.{Map, Seam, Delta}

      fog_a =
        Map.new("braid")
        |> Map.add("multi-star-prediction", :known_unknown, domain: "solar")
        |> Map.add("coronal-mass-ejection", :inferred_unknown, domain: "mesh")

      fog_b =
        Map.new("solver")
        |> Map.add("flare-induced-correction", :known_unknown, domain: "orbital")

      seam = Seam.measure(fog_a, fog_b)
      IO.puts Seam.summary(seam)
      # FogSeam(braid↔solver) tension=1.0 A-only=2 B-only=1 shared=0
      # — high-potential seam — asymmetric blind spots, strong transfer signal

      # Detect arbitrage
      fog_a2 = Map.add(fog_a, "new-gap", :known_unknown)
               |> then(fn f -> elem(Map.remove(f, "multi-star-prediction", "solar"), 0) end)

      delta = Delta.diff(fog_a, fog_a2)
      IO.puts Delta.summary(delta)
      # [braid] arbitrage — +1 -1 net=0 (ignorance redistributed, not reduced)

  For stateful fog (agent process), wrap Fog.Map in a GenServer:

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
