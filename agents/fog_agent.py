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
import os
import time
sys.path.insert(0, "/home/sophia/fog")
sys.path.insert(0, "/home/sophia/numinous")

WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOG_REPORT = os.path.join(WORKSPACE, "data", "fog", "fog-report.json")

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


# ─── Mesh Task Handlers (called by runner.py) ───────────────────────────

def handle_fog_read(data: dict) -> dict:
    """Handle fog/read topic."""
    return fog_read(data.get("args", {}))


def handle_seam_report(data: dict) -> dict:
    """Handle fog/seams topic."""
    return seam_report(data.get("args", {}))


def handle_dark_circles(data: dict) -> dict:
    """Handle fog/dark-circles topic."""
    return dark_circles(data.get("args", {}))


def handle_gap_inventory(data: dict) -> dict:
    """Handle fog/gaps topic."""
    return gap_inventory(data.get("args", {}))


def void_pressure(args: dict) -> dict:
    """Read void pressure from fog-report.json.

    The report nests core metrics under the `mesh` key:
      mesh.system_volume, mesh.system_entropy, mesh.dark_core_count, mesh.union_gaps
    plus seam tension under `seam.tension`.
    """
    try:
        with open(FOG_REPORT) as f:
            report = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return {"error": str(e), "readable": f"Could not read fog report: {e}"}

    mesh = report.get("mesh", {})
    seam = report.get("seam", {})

    volume = mesh.get("system_volume")
    entropy = mesh.get("system_entropy")
    dark_core_count = mesh.get("dark_core_count", 0)
    union_gaps = mesh.get("union_gaps", 0)
    seam_tension = seam.get("tension")
    seam_pair = f"{seam.get('agent_a', '?')}\u2194{seam.get('agent_b', '?')}" if seam else None

    # Void pressure heuristic: ratio of unknown mass to total agent coverage
    # High dark core count + high volume = high void pressure
    if volume is not None and volume > 0:
        pressure = (dark_core_count * 0.3 + union_gaps * 0.1) / volume
    else:
        pressure = 0.0

    return {
        "fog_volume": volume,
        "entropy": entropy,
        "dark_core_count": dark_core_count,
        "union_gaps": union_gaps,
        "seam_tension": seam_tension,
        "seam_pair": seam_pair,
        "void_pressure": round(pressure, 4),
        "readable": (
            f"Void pressure: {pressure:.4f} | "
            f"volume={volume} entropy={entropy} "
            f"dark_cores={dark_core_count} gaps={union_gaps} "
            f"seam={seam_pair} tension={seam_tension}"
            if volume is not None
            else "No fog volume data available."
        ),
    }


def handle_void_pressure(data: dict) -> dict:
    """Handle fog/void-pressure topic."""
    return void_pressure(data.get("args", {}))


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
        "void-pressure": void_pressure,
    }

    handler = dispatch.get(command)
    if not handler:
        print(json.dumps({"error": f"Unknown command: {command}", "available": list(dispatch.keys())}))
        sys.exit(1)

    result = handler(args)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
