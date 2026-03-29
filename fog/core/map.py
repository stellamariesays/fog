"""
FogMap — structured representation of an agent's ignorance.

Not absence of data. Not silence. The shape of what isn't known.
"""

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

DEFAULT_HALF_LIFE = 7 * 24 * 3600  # 7 days in seconds


class GapKind(Enum):
    KNOWN_UNKNOWN = "known_unknown"       # Agent knows it doesn't know this
    INFERRED_UNKNOWN = "inferred_unknown" # Gap inferred from seam topology
    STALE = "stale"                       # Once known, now uncertain


@dataclass
class Gap:
    """A single gap in an agent's knowledge."""
    key: str
    kind: GapKind
    domain: Optional[str] = None
    confidence: float = 1.0              # Confidence that this is actually a gap
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def touch(self):
        self.last_seen = time.time()

    def effective_confidence(self, half_life: float = DEFAULT_HALF_LIFE, at: float = None) -> float:
        """
        Confidence decays exponentially with time since last_seen.
            eff = confidence × exp(−λt)   where λ = ln(2) / half_life

        A gap unseen for one half_life period retains half its original confidence.
        STALE gaps carry an additional ×0.5 penalty at creation — they were known once.
        """
        t = (at or time.time()) - self.last_seen
        decay = math.exp(-math.log(2) / half_life * max(t, 0))
        stale_penalty = 0.5 if self.kind == GapKind.STALE else 1.0
        return self.confidence * decay * stale_penalty


class FogMap:
    """
    The map of what an agent doesn't know.

    Gaps are keyed by domain:key. Fog is not uniform — some regions
    are dense (high confidence), some thin, some decaying.
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.gaps: Dict[str, Gap] = {}
        self.created_at = time.time()

    def add(self, key: str, kind: GapKind, domain: str = None,
            confidence: float = 1.0, **metadata) -> Gap:
        full_key = f"{domain}:{key}" if domain else key
        if full_key in self.gaps:
            self.gaps[full_key].touch()
            return self.gaps[full_key]
        gap = Gap(key=full_key, kind=kind, domain=domain,
                  confidence=confidence, metadata=metadata)
        self.gaps[full_key] = gap
        return gap

    def remove(self, key: str, domain: str = None) -> bool:
        """Fog lifted on this gap — agent now knows."""
        full_key = f"{domain}:{key}" if domain else key
        if full_key in self.gaps:
            del self.gaps[full_key]
            return True
        return False

    def get(self, key: str, domain: str = None) -> Optional[Gap]:
        full_key = f"{domain}:{key}" if domain else key
        return self.gaps.get(full_key)

    def size(self) -> int:
        return len(self.gaps)

    def fog_volume(self, half_life: float = DEFAULT_HALF_LIFE) -> float:
        """
        Total effective ignorance — the L1 mass of the fog distribution.
        Sum of all effective confidences. Not normalised.
        Use this to compare raw amounts of ignorance over time.
        """
        return sum(g.effective_confidence(half_life) for g in self.gaps.values())

    def entropy(self, half_life: float = DEFAULT_HALF_LIFE) -> float:
        """
        Shannon entropy of the fog distribution.
            H = −Σ p_i log₂(p_i)   where p_i = eff_i / total_volume

        High H: ignorance is spread across many uncertain gaps.
        Low H:  ignorance is concentrated in a few high-confidence gaps.
        H = 0:  single gap (maximum concentration) or empty map.

        Note: entropy measures *shape*, not volume. An agent with 100 small
        gaps can have higher entropy than one with 3 large ones.
        """
        effs = [g.effective_confidence(half_life) for g in self.gaps.values()]
        total = sum(effs)
        if total == 0:
            return 0.0
        ps = [e / total for e in effs]
        return -sum(p * math.log2(p) for p in ps if p > 0)

    def by_domain(self) -> Dict[str, list]:
        result = {}
        for gap in self.gaps.values():
            d = gap.domain or "_global"
            result.setdefault(d, []).append(gap)
        return result

    def __repr__(self):
        return (f"FogMap(agent={self.agent_id}, gaps={self.size()}, "
                f"volume={self.fog_volume():.2f}, H={self.entropy():.2f})")
