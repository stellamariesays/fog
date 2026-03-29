"""
FogDelta — the change in fog between two states.

Weighted net < 0  →  fog lifted (new signal entered)
Weighted net ≈ 0  →  epistemic arbitrage (redistribution only)
Weighted net > 0  →  fog deepened
"""

import math
from dataclasses import dataclass, field
from typing import Optional, Set

from .map import FogMap, DEFAULT_HALF_LIFE

_EPS = 1e-9


@dataclass
class FogDelta:
    agent_id: str
    gaps_lifted: Set[str]     # Keys that disappeared (fog cleared)
    gaps_added: Set[str]      # Keys that appeared (fog deepened)
    gaps_unchanged: Set[str]  # Keys present in both snapshots
    _before: Optional[FogMap] = field(default=None, repr=False)
    _after: Optional[FogMap] = field(default=None, repr=False)
    half_life: float = field(default=DEFAULT_HALF_LIFE, repr=False)

    @property
    def net(self) -> float:
        """
        Weighted net change in fog volume.
            net = vol(added) − vol(lifted)

        Uses effective_confidence as weights.
        A high-confidence gap lifted is worth more than a decayed one added.
        Negative is good — fog is clearing. Zero is suspicious. Positive is bad.
        """
        if self._before is None or self._after is None:
            return float(len(self.gaps_added) - len(self.gaps_lifted))

        vol_added = sum(
            self._after.gaps[k].effective_confidence(self.half_life)
            for k in self.gaps_added if k in self._after.gaps
        )
        vol_lifted = sum(
            self._before.gaps[k].effective_confidence(self.half_life)
            for k in self.gaps_lifted if k in self._before.gaps
        )
        return vol_added - vol_lifted

    @property
    def entropy_delta(self) -> float:
        """
        Change in fog entropy between before and after.
            ΔH = H(after) − H(before)

        ΔH < 0: fog distribution became more concentrated — the agent's
                ignorance is now focused in fewer, better-defined gaps.
        ΔH > 0: fog spread out — the agent now has broader, more diffuse uncertainty.
        ΔH ≈ 0: same structural shape of ignorance (even if individual gaps changed).

        Note: entropy_delta is independent of volume. An agent can lift a gap
        and still have ΔH > 0 if the remaining distribution becomes more spread.
        """
        if self._before is None or self._after is None:
            return float('nan')
        return self._after.entropy(self.half_life) - self._before.entropy(self.half_life)

    @property
    def is_arbitrage(self) -> bool:
        """
        True if fog moved but total volume didn't shrink.
        Requires churn (gaps lifted AND added) with near-zero net.
        """
        has_churn = len(self.gaps_lifted) > 0 and len(self.gaps_added) > 0
        return has_churn and abs(self.net) < _EPS

    @property
    def is_lift(self) -> bool:
        """True if fog genuinely shrank — new signal entered."""
        return self.net < -_EPS

    @property
    def is_deepening(self) -> bool:
        """True if the agent knows less than before."""
        return self.net > _EPS

    def summary(self) -> str:
        ed = self.entropy_delta
        ed_str = f" ΔH={ed:+.3f}" if not math.isnan(ed) else ""

        if abs(self.net) < _EPS and len(self.gaps_lifted) == 0:
            return f"[{self.agent_id}] static — no change{ed_str}"
        if self.is_arbitrage:
            return (
                f"[{self.agent_id}] arbitrage — "
                f"+{len(self.gaps_added)} -{len(self.gaps_lifted)} "
                f"net={self.net:.3f} (ignorance redistributed, not reduced){ed_str}"
            )
        if self.is_lift:
            return f"[{self.agent_id}] lift — net={self.net:.3f} (fog clearing){ed_str}"
        return f"[{self.agent_id}] deepening — net=+{self.net:.3f} (fog growing){ed_str}"


def diff(before: FogMap, after: FogMap,
         half_life: float = DEFAULT_HALF_LIFE) -> FogDelta:
    """Compute the fog delta between two map snapshots."""
    before_keys = set(before.gaps.keys())
    after_keys = set(after.gaps.keys())
    return FogDelta(
        agent_id=before.agent_id,
        gaps_lifted=before_keys - after_keys,
        gaps_added=after_keys - before_keys,
        gaps_unchanged=before_keys & after_keys,
        _before=before,
        _after=after,
        half_life=half_life,
    )
