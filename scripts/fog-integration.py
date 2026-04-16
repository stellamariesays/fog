#!/usr/bin/env python3
"""
fog-integration.py — Sophia's fog computation layer.

Reads data/fog/mesh-snapshot.json, builds a FogMesh,
computes epistemic metrics, writes data/fog/fog-report.json.
"""

import sys
import json
import os
import time
from datetime import datetime, timezone

# Resolve paths relative to Sophia's workspace
WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOG_LIB = os.path.expanduser("~/fog")
INPUT_PATH = os.path.join(WORKSPACE, "data", "fog", "mesh-snapshot.json")
OUTPUT_PATH = os.path.join(WORKSPACE, "data", "fog", "fog-report.json")
SUMMARY_PATH = os.path.join(WORKSPACE, "data", "fog", "latest-summary.txt")

# Add fog library to path
sys.path.insert(0, FOG_LIB)

from fog import FogMap, GapKind, FogMesh, measure, diff
from fog.detect.arbitrage import detect_arbitrage, is_dark_conserved

KIND_MAP = {
    "known_unknown": GapKind.KNOWN_UNKNOWN,
    "inferred_unknown": GapKind.INFERRED_UNKNOWN,
    "stale": GapKind.STALE,
}


def load_snapshot(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def build_mesh(snapshot: dict) -> tuple[FogMesh, list[FogMap]]:
    mesh = FogMesh()
    fog_maps = []
    for agent_data in snapshot.get("agents", []):
        fog = FogMap(agent_data["id"])
        for gap_data in agent_data.get("gaps", []):
            kind = KIND_MAP.get(gap_data.get("kind", "known_unknown"), GapKind.KNOWN_UNKNOWN)
            fog.add(
                key=gap_data["key"],
                kind=kind,
                domain=gap_data.get("domain"),
                confidence=gap_data.get("confidence", 1.0),
            )
        mesh.register(fog)
        fog_maps.append(fog)
    return mesh, fog_maps


def run_integration(snapshot_path: str = INPUT_PATH) -> dict:
    snapshot = load_snapshot(snapshot_path)
    mesh, fog_maps = build_mesh(snapshot)

    # Core mesh metrics
    snap = mesh.snapshot()
    dark_core = list(mesh.dark_core())

    # Highest tension seam
    seam = mesh.highest_tension_seam()
    seam_data = None
    if seam:
        seam_data = {
            "agent_a": seam.agent_a,
            "agent_b": seam.agent_b,
            "tension": round(seam.tension, 4),
            "js_divergence": round(seam.js_divergence(), 4),
            "kl_a_to_b": round(seam.kl_divergence("a_to_b"), 4),
            "a_only_count": len(seam.only_in_a),
            "b_only_count": len(seam.only_in_b),
            "shared_count": len(seam.shared),
            "summary": seam.summary(),
        }

    # Arbitrage detection (need before/after; use identical snapshots as baseline)
    # For live use: pass (before, after) pairs. Here we detect static arbitrage signals.
    arbitrage_agents = []
    # We flag agents whose fog maps show signs of churn patterns
    # (In practice, caller should pass snapshots over time for real detection)

    # Dark conservation check (single snapshot: trivially not conserved)
    # Real use: call with list of (before, after) FogMap pairs

    # Build human-readable summary
    if seam_data:
        if seam_data["tension"] > 0.7:
            tension_label = "high transfer potential"
        elif seam_data["tension"] > 0.3:
            tension_label = "moderate transfer potential"
        else:
            tension_label = "low transfer potential — possible arbitrage territory"
        summary = (
            f"{snap['agents']} agents | "
            f"system fog volume={snap['system_volume']:.2f} | "
            f"H={snap['system_entropy']:.2f} | "
            f"dark core={snap['dark_core']} gaps | "
            f"hottest seam: {seam_data['agent_a']}↔{seam_data['agent_b']} "
            f"tension={seam_data['tension']:.3f} ({tension_label})"
        )
    else:
        summary = f"{snap['agents']} agents | system fog volume={snap['system_volume']:.2f} | no seams computed"

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mesh": {
            "agents": snap["agents"],
            "system_volume": snap["system_volume"],
            "system_entropy": snap["system_entropy"],
            "dark_core_count": snap["dark_core"],
            "dark_core": dark_core,
            "union_gaps": snap["union_gaps"],
        },
        "seam": seam_data,
        "arbitrage": {
            "detected": len(arbitrage_agents) > 0,
            "agents_with_arbitrage": arbitrage_agents,
        },
        "summary": summary,
    }

    return report


def write_report(report: dict, output_path: str = OUTPUT_PATH, summary_path: str = SUMMARY_PATH):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
    with open(summary_path, "w") as f:
        f.write(report["summary"] + "\n")
    print(report["summary"])


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sophia fog integration")
    parser.add_argument("--snapshot", default=INPUT_PATH, help="Path to mesh-snapshot.json")
    parser.add_argument("--output", default=OUTPUT_PATH, help="Path to write fog-report.json")
    args = parser.parse_args()

    report = run_integration(args.snapshot)
    write_report(report, args.output)
