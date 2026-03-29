"""
FogSeam — boundary region between two agents' fog states.

High seam tension = agents have different blind spots = transfer potential.
Zero tension = same fog everywhere = pure arbitrage territory.
"""

import math
from dataclasses import dataclass, field
from typing import Optional, Set

from .map import FogMap, DEFAULT_HALF_LIFE

_SMOOTH = 1e-9  # epsilon for KL where a gap is absent in one distribution


@dataclass
class FogSeam:
    agent_a: str
    agent_b: str
    only_in_a: Set[str]   # A has fog here; B might have signal
    only_in_b: Set[str]   # B has fog here; A might have signal
    shared: Set[str]      # Both dark — genuine system gap, needs external signal
    _map_a: Optional[FogMap] = field(default=None, repr=False)
    _map_b: Optional[FogMap] = field(default=None, repr=False)
    half_life: float = field(default=DEFAULT_HALF_LIFE, repr=False)

    @property
    def tension(self) -> float:
        """
        Weighted seam tension: fraction of total fog volume that is asymmetric.

            tension = vol(A-only ∪ B-only) / vol(A ∪ B)

        Uses effective_confidence as weights. A high-confidence gap in A-only
        contributes more tension than a decayed one.

        1.0 = perfectly asymmetric blind spots (maximum transfer potential)
        0.0 = identical fog on both sides (pure arbitrage territory)
        """
        if self._map_a is None or self._map_b is None:
            # Unweighted fallback
            total = len(self.only_in_a) + len(self.only_in_b) + len(self.shared)
            return (len(self.only_in_a) + len(self.only_in_b)) / total if total else 0.0

        def eff(fmap, keys):
            return sum(
                fmap.gaps[k].effective_confidence(self.half_life)
                for k in keys if k in fmap.gaps
            )

        vol_asym = eff(self._map_a, self.only_in_a) + eff(self._map_b, self.only_in_b)
        vol_shared = sum(
            max(
                self._map_a.gaps[k].effective_confidence(self.half_life) if k in self._map_a.gaps else 0.0,
                self._map_b.gaps[k].effective_confidence(self.half_life) if k in self._map_b.gaps else 0.0,
            )
            for k in self.shared
        )
        total = vol_asym + vol_shared
        return vol_asym / total if total > 0 else 0.0

    def kl_divergence(self, direction: str = "a_to_b") -> float:
        """
        KL divergence between the two fog distributions.
            D_KL(A ∥ B) = Σ p_A(x) log(p_A(x) / p_B(x))

        Interpretation:
            D_KL(A→B): how surprised B's fog structure would be by A's.
            D_KL(B→A): reverse.

        Asymmetric by design — A's surprise at B ≠ B's surprise at A.
        Gaps absent in one distribution are smoothed with ε = 1e-9.

        High value: the two fog maps are structurally very different.
        Near zero: similar fog distribution shapes (even if volumes differ).
        """
        if self._map_a is None or self._map_b is None:
            return float('nan')

        universe = set(self._map_a.gaps.keys()) | set(self._map_b.gaps.keys())
        vol_a = self._map_a.fog_volume(self.half_life) or 1.0
        vol_b = self._map_b.fog_volume(self.half_life) or 1.0

        def pa(k):
            g = self._map_a.gaps.get(k)
            return g.effective_confidence(self.half_life) / vol_a if g else _SMOOTH

        def pb(k):
            g = self._map_b.gaps.get(k)
            return g.effective_confidence(self.half_life) / vol_b if g else _SMOOTH

        if direction == "a_to_b":
            return sum(pa(k) * math.log(pa(k) / pb(k)) for k in universe)
        else:
            return sum(pb(k) * math.log(pb(k) / pa(k)) for k in universe)

    def js_divergence(self) -> float:
        """
        Jensen-Shannon divergence — the symmetric cousin of KL.
            JS(A, B) = ½ D_KL(A ∥ M) + ½ D_KL(B ∥ M)   where M = (A + B) / 2

        Bounded [0, 1] in bits (log₂ base).
        Use when you want a single number for "how different are these fog maps"
        without caring which direction the surprise runs.

        0.0 = identical distributions
        1.0 = completely disjoint fog (no overlap at all)
        """
        if self._map_a is None or self._map_b is None:
            return float('nan')

        universe = set(self._map_a.gaps.keys()) | set(self._map_b.gaps.keys())
        vol_a = self._map_a.fog_volume(self.half_life) or 1.0
        vol_b = self._map_b.fog_volume(self.half_life) or 1.0

        def pa(k):
            g = self._map_a.gaps.get(k)
            return g.effective_confidence(self.half_life) / vol_a if g else _SMOOTH

        def pb(k):
            g = self._map_b.gaps.get(k)
            return g.effective_confidence(self.half_life) / vol_b if g else _SMOOTH

        def kl_term(p, q):
            return p * math.log2(p / q) if p > 0 else 0.0

        total = 0.0
        for k in universe:
            p, q = pa(k), pb(k)
            m = (p + q) / 2
            total += 0.5 * kl_term(p, m) + 0.5 * kl_term(q, m)
        return total

    @property
    def system_gaps(self) -> Set[str]:
        """Gaps neither agent can fill from the other — need external signal."""
        return self.shared

    def summary(self) -> str:
        parts = [
            f"FogSeam({self.agent_a}↔{self.agent_b})",
            f"tension={self.tension:.3f}",
            f"A-only={len(self.only_in_a)}",
            f"B-only={len(self.only_in_b)}",
            f"shared={len(self.shared)}",
        ]
        kl = self.kl_divergence()
        js = self.js_divergence()
        if not math.isnan(kl):
            parts.append(f"KL(A→B)={kl:.3f}")
        if not math.isnan(js):
            parts.append(f"JS={js:.3f}")
        return " ".join(parts)


def measure(map_a: FogMap, map_b: FogMap,
            half_life: float = DEFAULT_HALF_LIFE) -> FogSeam:
    """Measure the seam between two agents' fog maps."""
    a_keys = set(map_a.gaps.keys())
    b_keys = set(map_b.gaps.keys())
    return FogSeam(
        agent_a=map_a.agent_id,
        agent_b=map_b.agent_id,
        only_in_a=a_keys - b_keys,
        only_in_b=b_keys - a_keys,
        shared=a_keys & b_keys,
        _map_a=map_a,
        _map_b=map_b,
        half_life=half_life,
    )
