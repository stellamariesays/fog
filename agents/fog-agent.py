#!/usr/bin/env python3
"""
Fog Reader Agent — task-executable wrapper around the fog library.

Commands:
    fog-read          → Full fog map summary (gaps, tension, pressure)
    seam-report       → Seam tension between known agents
    dark-circles      → List current dark circles
    gap-inventory     → Structured gap list by domain

Input: JSON args on argv[2] (optional)
Output: JSON on stdout
"""

import sys
import json
import time
sys.path.insert(0, "/home/sophia/fog")
sys.path.insert(0, "/home/sophia/numinous")

from fog.core.map import FogMap, Gap, GapKind
from fog.core.seam import FogSeam


def _load_or_empty_fog(agent_id: str = "sophia") -> FogMap:
    """Try loading a persisted fog map, else return empty."""
    fmap = FogMap(agent_id)
    # TODO: load from ~/data/fog-maps/ when persistence is wired
    return fmap


def fog_read(args: dict) -> dict:
    fmap = _load_or_empty_fog()
    gaps = list(fmap.gaps.values())
    return {
        "agent": fmap.agent_id,
        "gap_count": len(gaps),
        "domains": list(set(g.domain or "unspecified" for g in gaps)),
        "gaps": [
            {
                "key": g.key,
                "kind": g.kind.value,
                "domain": g.domain,
                "confidence": round(g.effective_confidence(), 4),
            }
            for g in gaps
        ],
        "readable": f"Fog map for {fmap.agent_id}: {len(gaps)} gaps across {len(set(g.domain or 'unspecified' for g in gaps))} domains.",
    }


def seam_report(args: dict) -> dict:
    """Report seam tension between known mesh agents."""
    # Build minimal fog maps from mesh knowledge
    agents = args.get("agents", ["sophia", "stella", "eddie"])
    seams = []

    # For now, return seam structure with what we know
    # Full implementation needs atlas data from Manifold
    for i, a in enumerate(agents):
        for b in agents[i+1:]:
            seam = FogSeam(
                agent_a=a,
                agent_b=b,
                only_in_a=set(),
                only_in_b=set(),
                shared=set(),
            )
            seams.append({
                "pair": f"{a}↔{b}",
                "tension": round(seam.tension, 4),
            })

    return {
        "seams": seams,
        "readable": f"Seam report: {len(seams)} agent pairs analyzed.",
    }


def dark_circles(args: dict) -> dict:
    """Fetch dark circles from the Manifold hub."""
    import urllib.request
    try:
        req = urllib.request.Request("http://localhost:8777/dark-circles")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        return {
            "source": "manifold-hub",
            "circles": data if isinstance(data, list) else data.get("circles", []),
            "readable": f"Dark circles: {len(data) if isinstance(data, list) else len(data.get('circles', []))} found.",
        }
    except Exception as e:
        return {"error": str(e), "readable": f"Could not read dark circles: {e}"}


def gap_inventory(args: dict) -> dict:
    fmap = _load_or_empty_fog()
    by_domain = {}
    for g in fmap.gaps.values():
        dom = g.domain or "unspecified"
        by_domain.setdefault(dom, []).append({
            "key": g.key,
            "kind": g.kind.value,
            "confidence": round(g.effective_confidence(), 4),
        })
    return {
        "domains": by_domain,
        "total_gaps": sum(len(v) for v in by_domain.values()),
        "readable": f"Gap inventory: {sum(len(v) for v in by_domain.values())} gaps in {len(by_domain)} domains.",
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No command. Usage: fog-agent.py <command> [args_json]"}))
        sys.exit(1)

    command = sys.argv[1]
    args = {}
    if len(sys.argv) > 2:
        try:
            args = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            args = {}

    dispatch = {
        "fog-read": fog_read,
        "seam-report": seam_report,
        "dark-circles": dark_circles,
        "gap-inventory": gap_inventory,
    }

    handler = dispatch.get(command)
    if not handler:
        print(json.dumps({"error": f"Unknown command: {command}", "available": list(dispatch.keys())}))
        sys.exit(1)

    result = handler(args)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
