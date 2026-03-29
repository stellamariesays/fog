"""
Detect epistemic arbitrage across a mesh of agents.

Arbitrage: ignorance is moving but not shrinking.
The system looks more informed. The total dark is unchanged.
"""

from typing import List, Tuple
from ..core.map import FogMap
from ..core.delta import FogDelta, diff


def detect_arbitrage(snapshots: List[Tuple[FogMap, FogMap]]) -> List[FogDelta]:
    """
    Given a list of (before, after) FogMap pairs across agents,
    return deltas flagged as epistemic arbitrage.

    A mesh is in arbitrage if:
    - Individual agents show gap churn (gaps lifted AND added)
    - Total system gap count doesn't decrease
    """
    deltas = [diff(before, after) for before, after in snapshots]
    return [d for d in deltas if d.is_arbitrage]


def system_fog_change(snapshots: List[Tuple[FogMap, FogMap]]) -> int:
    """
    Net change in total system ignorance across all agents.
    Negative = fog actually lifted somewhere.
    Zero = pure redistribution.
    Positive = system knows less than before.
    """
    return sum(diff(before, after).net for before, after in snapshots)
