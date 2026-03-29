"""
FogSeam — boundary region between two agents' fog states.

This is where Manifold's Sophia signal hooks in.
High seam density = agents disagree on what they don't know.
That disagreement is itself signal.
"""

from dataclasses import dataclass
from typing import Set
from .map import FogMap


@dataclass
class FogSeam:
    agent_a: str
    agent_b: str
    only_in_a: Set[str]   # Gaps A has that B doesn't — B may have signal A lacks
    only_in_b: Set[str]   # Gaps B has that A doesn't — A may have signal B lacks
    shared: Set[str]      # Both dark on this — genuine system gap

    @property
    def tension(self) -> float:
        """
        Seam tension: ratio of asymmetric gaps to total.
        High tension = agents have different blind spots = transfer potential.
        Zero tension = same fog everywhere = pure arbitrage territory.
        """
        total = len(self.only_in_a) + len(self.only_in_b) + len(self.shared)
        if total == 0:
            return 0.0
        asymmetric = len(self.only_in_a) + len(self.only_in_b)
        return asymmetric / total

    @property
    def system_gaps(self) -> Set[str]:
        """Gaps neither agent can fill from the other — need external signal."""
        return self.shared

    def summary(self) -> str:
        return (
            f"Seam({self.agent_a}↔{self.agent_b}) "
            f"tension={self.tension:.2f} "
            f"A-only={len(self.only_in_a)} "
            f"B-only={len(self.only_in_b)} "
            f"shared={len(self.shared)}"
        )


def measure(map_a: FogMap, map_b: FogMap) -> FogSeam:
    """Measure the seam between two agents' fog maps."""
    a_keys = set(map_a.gaps.keys())
    b_keys = set(map_b.gaps.keys())

    return FogSeam(
        agent_a=map_a.agent_id,
        agent_b=map_b.agent_id,
        only_in_a=a_keys - b_keys,
        only_in_b=b_keys - a_keys,
        shared=a_keys & b_keys,
    )
