"""
FogMesh — multi-agent fog layer with propagation.

Tracks fog across N agents. When one agent lifts fog on a key,
propagates reduced confidence to others who hold INFERRED_UNKNOWN on that key.
"""

import math
from typing import Dict, List, Optional, Set, Tuple

from ..core.map import FogMap, GapKind, DEFAULT_HALF_LIFE
from ..core.seam import FogSeam, measure
from ..core.delta import FogDelta, diff

# When an agent lifts fog, how much does that reduce others' inferred confidence?
_PROPAGATION_FACTOR = 0.5


class FogMesh:
    """
    A mesh of N agents' fog maps with propagation rules.

    The propagation rule is deliberate:
    When agent A lifts fog on key X, other agents holding INFERRED_UNKNOWN
    on X see their confidence reduced — the source of their inference
    (that X is universally unknown) no longer holds.

    The dark core is what no internal propagation can touch — gaps that
    require external signal to resolve.
    """

    def __init__(self, half_life: float = DEFAULT_HALF_LIFE):
        self.agents: Dict[str, FogMap] = {}
        self.half_life = half_life

    def register(self, fog_map: FogMap) -> "FogMesh":
        """Add an agent's fog map to the mesh. Returns self for chaining."""
        self.agents[fog_map.agent_id] = fog_map
        return self

    def propagate_lift(self, agent_id: str, key: str,
                       domain: str = None,
                       factor: float = _PROPAGATION_FACTOR) -> List[str]:
        """
        Called when agent_id lifts fog on key.

        Propagation rule:
            For every other agent holding INFERRED_UNKNOWN on the same key,
            multiply their confidence by `factor` (default 0.5).

        The intuition: INFERRED_UNKNOWN gaps are derived from topology —
        "I don't know this because no one in my mesh does."
        If someone in the mesh now knows it, the inference weakens.

        Returns list of agent IDs whose fog was updated.
        """
        full_key = f"{domain}:{key}" if domain else key
        updated = []
        for aid, fmap in self.agents.items():
            if aid == agent_id:
                continue
            gap = fmap.gaps.get(full_key)
            if gap and gap.kind == GapKind.INFERRED_UNKNOWN:
                gap.confidence = max(gap.confidence * factor, 0.0)
                gap.touch()
                updated.append(aid)
        return updated

    def total_fog_volume(self) -> float:
        """
        Sum of all effective confidences across all agents.
        Not deduplicated — shared gaps count once per agent.
        Use system_fog_volume() for deduplicated totals.
        """
        return sum(fmap.fog_volume(self.half_life) for fmap in self.agents.values())

    def system_fog_volume(self) -> float:
        """
        Deduplicated fog volume: each gap key counted once at max confidence.
        Measures actual system ignorance, not agent-redundant ignorance.
        """
        key_max: Dict[str, float] = {}
        for fmap in self.agents.values():
            for k, gap in fmap.gaps.items():
                eff = gap.effective_confidence(self.half_life)
                key_max[k] = max(key_max.get(k, 0.0), eff)
        return sum(key_max.values())

    def system_entropy(self) -> float:
        """
        Shannon entropy of the total mesh fog distribution.
        Treats all gaps across all agents as a single flat distribution.
        High entropy = ignorance spread diffusely across the whole mesh.
        Low entropy = most ignorance concentrated in a few high-signal gaps.
        """
        effs = [
            gap.effective_confidence(self.half_life)
            for fmap in self.agents.values()
            for gap in fmap.gaps.values()
        ]
        total = sum(effs)
        if total == 0:
            return 0.0
        return -sum(
            (e / total) * math.log2(e / total)
            for e in effs if e > 0
        )

    def union_gaps(self) -> Set[str]:
        """All gap keys present in any agent."""
        return set().union(*(set(fmap.gaps.keys()) for fmap in self.agents.values()))

    def dark_core(self) -> Set[str]:
        """
        Gaps present in ALL agents — genuine system-wide blind spots.
        No internal propagation can touch these.
        External signal required.
        """
        if not self.agents:
            return set()
        return set.intersection(*(set(fmap.gaps.keys()) for fmap in self.agents.values()))

    def seam_matrix(self) -> Dict[Tuple[str, str], FogSeam]:
        """All pairwise seams across the mesh."""
        agents = list(self.agents.values())
        result = {}
        for i, a in enumerate(agents):
            for b in agents[i + 1:]:
                result[(a.agent_id, b.agent_id)] = measure(a, b, self.half_life)
        return result

    def highest_tension_seam(self) -> Optional[FogSeam]:
        """Which pair of agents has the most to offer each other?"""
        matrix = self.seam_matrix()
        if not matrix:
            return None
        return max(matrix.values(), key=lambda s: s.tension)

    def snapshot(self) -> dict:
        """Summary metrics for the current mesh state."""
        return {
            "agents": len(self.agents),
            "total_volume": round(self.total_fog_volume(), 3),
            "system_volume": round(self.system_fog_volume(), 3),
            "system_entropy": round(self.system_entropy(), 3),
            "union_gaps": len(self.union_gaps()),
            "dark_core": len(self.dark_core()),
        }

    def __repr__(self):
        s = self.snapshot()
        return (f"FogMesh(agents={s['agents']}, "
                f"system_volume={s['system_volume']:.2f}, "
                f"H={s['system_entropy']:.2f}, "
                f"dark_core={s['dark_core']})")
