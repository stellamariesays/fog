"""
Detect epistemic arbitrage across a mesh of agents.

Arbitrage: ignorance is moving but not shrinking.
The system looks more informed. The total dark is conserved.

Two levels of detection:
  - Agent level: individual delta flagged as arbitrage (churn, near-zero net)
  - Mesh level: total system fog volume didn't change despite individual churn
"""

import math
from typing import List, Tuple

from ..core.map import FogMap, DEFAULT_HALF_LIFE
from ..core.delta import FogDelta, diff


def detect_arbitrage(
    snapshots: List[Tuple[FogMap, FogMap]],
    half_life: float = DEFAULT_HALF_LIFE,
) -> List[FogDelta]:
    """
    Given (before, after) pairs across agents, return deltas flagged as arbitrage.
    Uses weighted net (effective_confidence) not raw gap counts.
    """
    deltas = [diff(before, after, half_life) for before, after in snapshots]
    return [d for d in deltas if d.is_arbitrage]


def system_fog_change(
    snapshots: List[Tuple[FogMap, FogMap]],
    half_life: float = DEFAULT_HALF_LIFE,
) -> float:
    """
    Weighted net change in total system ignorance across all agents.
    Negative = fog actually lifted somewhere.
    Zero     = pure redistribution (dark conservation).
    Positive = system knows less than before.
    """
    return sum(diff(before, after, half_life).net for before, after in snapshots)


def system_entropy_change(
    snapshots: List[Tuple[FogMap, FogMap]],
    half_life: float = DEFAULT_HALF_LIFE,
) -> float:
    """
    Net change in total system entropy across all agents.
    Measures whether the *structure* of ignorance changed, independent of volume.

    Negative = fog distribution became more concentrated system-wide.
    Zero     = same entropy shape (even with churn).
    Positive = fog spread out — broader, more diffuse uncertainty.
    """
    total = sum(diff(before, after, half_life).entropy_delta
                for before, after in snapshots)
    return total if not math.isnan(total) else float('nan')


def is_dark_conserved(
    snapshots: List[Tuple[FogMap, FogMap]],
    half_life: float = DEFAULT_HALF_LIFE,
    tolerance: float = 1e-6,
) -> bool:
    """
    True if total system fog volume is conserved across all agent changes.
    This is the mesh-level dark conservation law:
        Σ vol(after_i) − Σ vol(before_i) ≈ 0
    despite individual agents showing churn.
    """
    return abs(system_fog_change(snapshots, half_life)) < tolerance
