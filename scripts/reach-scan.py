#!/usr/bin/env python3
"""
reach-scan.py — Sophia's fog heartbeat
Runs reach_scan against the known mesh agents, writes results to memory/void-state.md
"""
import sys
import json
from datetime import datetime, timezone

sys.path.insert(0, '/home/sophia/venv/lib/python3.12/site-packages')

from core.atlas import Atlas
from core.registry import CapabilityRegistry
from numinous.reach import reach_scan

# Known mesh agents — update as new agents join
AGENTS = {
    "stella":       (["judgment", "conversation", "strategy", "memory-search", "terrain-tracking", "session-management"], "100.64.0.1"),
    "eddie":        (["mesh-architecture", "federation-design", "reach-scan", "numinous-integration", "void-detection", "atlas-building"], "100.64.0.2"),
    "sophia":       (["fog-analysis", "dark-circle-detection", "seam-monitoring", "void-watching", "fog-integration"], "100.124.38.123"),
    "braid":        (["signal-composition", "backtest-strategy", "model-training", "threshold-detection", "feature-engineering"], "100.64.0.3"),
    "solar-detect": (["solar-monitoring", "swpc-ingestion", "alert-detection", "threshold-sweep", "realtime-monitor"], "100.64.0.4"),
    "clawstreet":   (["trade-execution", "position-management", "portfolio-tracking", "market-analysis"], "100.64.0.5"),
    "poreee":       (["block-mining", "ledger-tracking", "crypto-identity", "proof-of-work"], "100.64.0.6"),
}

def run():
    reg = CapabilityRegistry()
    for name, (caps, addr) in AGENTS.items():
        reg.register_self(name, caps, addr)

    atlas = Atlas.build(reg)
    reading = reach_scan(atlas)
    
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    
    # Write void-state.md
    lines = [
        f"# Void State — Current Dark Circles",
        f"*Last scan: {now}*",
        f"",
        f"## Summary",
        f"{reading.interpretation}",
        f"",
        f"## Candidate Regions ({len(reading.candidate_regions)} found)",
    ]
    for r in reading.candidate_regions[:10]:
        lines.append(f"- **[{r.strength:.3f}]** `{r.term}` — implied by: {', '.join(r.implied_by[:4])}")
    
    lines += ["", "## Raw JSON"]
    raw = [{"term": r.term, "strength": r.strength, "implied_by": r.implied_by} 
           for r in reading.candidate_regions]
    lines.append(f"```json\n{json.dumps(raw[:10], indent=2)}\n```")
    
    with open('/home/sophia/openclaw-workspace/sophia/memory/void-state.md', 'w') as f:
        f.write('\n'.join(lines))
    
    print(f"[{now}] reach_scan complete: {len(reading.candidate_regions)} regions")
    print(f"Top: [{reading.candidate_regions[0].strength:.3f}] {reading.candidate_regions[0].term}")
    return reading

if __name__ == '__main__':
    run()
