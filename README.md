# FOG

> *Epistemic fog mapping for agent meshes.*

FOG tracks what agents **don't** know — not what they do.

---

## The Problem

Most agent systems map knowledge: what has been seen, remembered, shared.
FOG maps the inverse: the shape of ignorance.

Two failure modes it exists to expose:

1. **Epistemic arbitrage** — shuffling existing ignorance between agents without reducing total system ignorance. Agents get better-distributed maps; the total dark doesn't shrink.
2. **Dark conservation** — mistaking redistribution for discovery. The sum of unknowns is conserved even as the system looks more informed.

---

## Concepts

**FogMap** — The agent's map of what it doesn't know. Not absence of data — structured representation of gaps: known unknowns, unknown unknowns (inferred from seam topology), and stale zones (once known, now uncertain).

**FogReading** — A snapshot of an agent's fog state at a point in time.

**FogDelta** — The change in fog between two readings. Negative delta = fog lifted (new signal). Zero delta = epistemic arbitrage. Positive delta = fog deepened.

**FogSeam** — Boundary region between what two agents know differently. Where Manifold's Sophia signal will eventually hook in.

---

## Structure

```
fog/
  core/
    map.py        # FogMap — gap representation
    reading.py    # FogReading — snapshot
    delta.py      # FogDelta — change detection
    seam.py       # FogSeam — boundary between agent fog states
  detect/
    arbitrage.py  # Detect epistemic arbitrage (zero-sum redistribution)
    lift.py       # Detect genuine fog lifting (new signal entry)
  store/
    memory.py     # Fog persistence (in-memory + file)
```

---

## Status

Early scaffold. Concepts defined, core structures in progress.

Will integrate into [Manifold](https://github.com/stellamariesays/Manifold) as the epistemic layer once the standalone proof of concept is stable.

---

*Part of the Stella/Hal cognitive mesh architecture.*
