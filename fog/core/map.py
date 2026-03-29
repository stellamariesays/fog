"""
FogMap — structured representation of an agent's ignorance.

Not absence of data. Not silence. The shape of what isn't known.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional
import time


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


class FogMap:
    """
    The map of what an agent doesn't know.

    Gaps are keyed by domain:key. Fog is not uniform — some regions
    are dense, some thin, some stale.
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.gaps: Dict[str, Gap] = {}
        self.created_at = time.time()

    def add(self, key: str, kind: GapKind, domain: str = None, **metadata) -> Gap:
        full_key = f"{domain}:{key}" if domain else key
        if full_key in self.gaps:
            self.gaps[full_key].touch()
            return self.gaps[full_key]
        gap = Gap(key=full_key, kind=kind, domain=domain, metadata=metadata)
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

    def by_domain(self) -> Dict[str, list]:
        result = {}
        for gap in self.gaps.values():
            d = gap.domain or "_global"
            result.setdefault(d, []).append(gap)
        return result

    def __repr__(self):
        return f"FogMap(agent={self.agent_id}, gaps={self.size()})"
