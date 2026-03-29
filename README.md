# FOG

> *Epistemic fog mapping for agent meshes.*

FOG tracks what agents **don't** know — not what they do.

Three implementations. Pick the one that fits your shape.

| | Python | Elixir | Haskell |
|---|---|---|---|
| **Shape** | library | service / process | library |
| **Best for** | Manifold integration, AI/ML pipelines | distributed meshes, stateful agents | type-safe embedding, compile-time guarantees |
| **FogMap is** | mutable object | immutable struct + optional GenServer | immutable value |
| **Runs as** | import | process or node | import |
| **Dir** | `fog/` | `elixir/` | `haskell/` |

---

## The Problem

Most agent systems map knowledge: what has been seen, remembered, shared.
FOG maps the inverse: the shape of ignorance.

Two failure modes it exists to expose:

1. **Epistemic arbitrage** — shuffling existing ignorance between agents without reducing total system ignorance. Agents get better-distributed maps; the total dark doesn't shrink.
2. **Dark conservation** — mistaking redistribution for discovery. The sum of unknowns is conserved even as the system looks more informed.

---

## Concepts

**FogMap** — The agent's map of what it doesn't know. Gaps carry confidence weights that decay exponentially with time (half-life configurable, default 7 days). STALE gaps get an additional ×0.5 penalty.

**FogDelta** — Change between two snapshots. `net` = weighted volume change (negative = good). `entropy_delta` = change in fog *structure*, independent of volume.

**FogSeam** — Boundary between two agents' fog states. `tension` = weighted asymmetric fraction. `kl_divergence` = directional structural distance. `js_divergence` = symmetric distance, bounded [0,1].

**FogMesh** — Multi-agent layer. `propagate_lift` reduces confidence on inferred unknowns when a source agent learns. `dark_core` = gaps in every agent (needs external signal). `system_entropy` = total mesh ignorance shape.

## Math

| Concept | Formula |
|---|---|
| Temporal decay | `eff = conf × exp(−ln(2)/half_life × t)` |
| Fog volume | `vol = Σ eff_i` |
| Fog entropy | `H = −Σ (eff_i/vol) log₂(eff_i/vol)` |
| Seam tension | `vol(asymmetric) / vol(total)` |
| KL divergence | `Σ p_A log(p_A / p_B)` |
| JS divergence | `½ KL(A∥M) + ½ KL(B∥M)` where `M=(A+B)/2` |
| Arbitrage | churn with `\|net\| ≈ 0` |
| Dark conservation | `Σ net_i ≈ 0` across all agents |

---

## Python

The reference implementation. Integrates directly into [Manifold](https://github.com/stellamariesays/Manifold) as `agent.fog()` and `agent.fog_seam()`.

```python
from fog import FogMap, GapKind, diff, measure

a = FogMap("braid")
a.add("multi-star-prediction", GapKind.KNOWN_UNKNOWN, domain="solar")
a.add("coronal-mass-ejection", GapKind.INFERRED_UNKNOWN, domain="mesh")

b = FogMap("solver")
b.add("flare-induced-correction", GapKind.KNOWN_UNKNOWN, domain="orbital")

seam = measure(a, b)
print(seam.summary())
# FogSeam(braid↔solver) tension=1.0 A-only=2 B-only=1 shared=0
# — high-potential seam — asymmetric blind spots, strong transfer signal

before = a
a.add("new-gap", GapKind.KNOWN_UNKNOWN)
a.remove("multi-star-prediction", domain="solar")
delta = diff(before, a)
print(delta.summary())
# [braid] arbitrage — +1 -1 net=0 (ignorance redistributed, not reduced)
```

**Pick Python when:** you're working in the AI/ML stack, integrating with Manifold, or prototyping.

---

## Elixir

FOG as a service. FogMap is an immutable struct. Agents are GenServers that hold fog state. The pipe operator makes fog pipelines read naturally. The right shape when FOG runs as a process the mesh queries — not a library it imports.

```elixir
alias Fog.{Map, Seam, Delta}

fog_a =
  Map.new("braid")
  |> Map.add("multi-star-prediction", :known_unknown, domain: "solar")
  |> Map.add("coronal-mass-ejection", :inferred_unknown, domain: "mesh")

fog_b =
  Map.new("solver")
  |> Map.add("flare-induced-correction", :known_unknown, domain: "orbital")

fog_a |> Seam.measure(fog_b) |> Seam.summary() |> IO.puts()
# FogSeam(braid↔solver) tension=1.0 A-only=2 B-only=1 shared=0
# — high-potential seam — asymmetric blind spots, strong transfer signal

fog_a2 = Map.add(fog_a, "new-gap", :known_unknown)
delta  = Delta.diff(fog_a, fog_a2)
IO.puts Delta.summary(delta)
# [braid] deepening — net=+1
```

Stateful agent (wrap in GenServer):

```elixir
defmodule FogAgent do
  use GenServer
  def init(agent_id),                       do: {:ok, Fog.Map.new(agent_id)}
  def handle_call({:add, key, kind, opts},  _, fog), do: {:reply, :ok,  Fog.Map.add(fog, key, kind, opts)}
  def handle_call(:snapshot,                _, fog), do: {:reply, fog,  fog}
end
```

**Pick Elixir when:** FOG runs as a distributed service, agents are long-lived processes, or you want fault tolerance and supervision built in.

---

## Haskell

FOG as types-as-spec. The type system makes mutation structurally impossible — fog states are values, not objects. Pattern matching on `GapKind`, `DeltaKind`, `SeamInterpretation` replaces conditionals. The compiler enforces that `diff` is a pure function before you run a line.

```haskell
import Fog.Map
import Fog.Gap
import Fog.Delta
import Fog.Seam

fogA :: FogMap
fogA = addGap (newGap "multi-star-prediction" KnownUnknown (Just "solar"))
     . addGap (newGap "coronal-mass-ejection" InferredUnknown (Just "mesh"))
     $ emptyFog "braid"

fogB :: FogMap
fogB = addGap (newGap "flare-induced-correction" KnownUnknown (Just "orbital"))
     $ emptyFog "solver"

main :: IO ()
main = do
  let seam  = measure fogA fogB
  putStrLn $ summarise seam
  -- FogSeam(braid↔solver) tension=1.0 A-only=2 B-only=1 shared=0
  -- — high-potential seam — asymmetric blind spots, strong transfer signal

  let fogA' = addGap (newGap "new-gap" KnownUnknown Nothing) fogA
      delta  = diff fogA fogA'
  putStrLn $ summarise delta
  -- [braid] deepening — net=+1
```

**Pick Haskell when:** you want the type system to do the thinking, you're embedding FOG in a Haskell agent, or you want compile-time proof that your fog operations are pure.

---

## Structure

```
fog/                     # Python (reference)
  core/
    map.py
    delta.py
    seam.py
  detect/
    arbitrage.py

elixir/                  # Elixir (service shape)
  lib/fog/
    gap.ex
    map.ex
    delta.ex
    seam.ex
    detect/
      arbitrage.ex

haskell/                 # Haskell (types-as-spec)
  src/Fog/
    Gap.hs
    Map.hs
    Delta.hs
    Seam.hs
    Detect/
      Arbitrage.hs
```

---

## Manifold integration

The Python implementation integrates into [Manifold](https://github.com/stellamariesays/Manifold) as the epistemic layer:

```python
# agent.fog() derives FogMap from Manifold's existing signals:
# - blind_spot() → KNOWN_UNKNOWN gaps
# - atlas().holes() → INFERRED_UNKNOWN gaps

fog_map = agent.fog()
seam    = agent.fog_seam(other_agent.fog())
print(seam.tension)   # epistemic inverse of the Sophia gradient
```

`FogSeam.tension` is the epistemic inverse of the Sophia gradient: where to route next based on what agents *don't* know.

---

*Part of the Stella/Hal cognitive mesh architecture.*
