#!/usr/bin/env python3
"""
fog-watch.py — Sophia's continuous fog monitor.

Runs fog-integration on a loop (default 60s) or once with --once.
Prints a human-readable summary each cycle to stdout.
Sophia's heartbeat can read data/fog/latest-summary.txt for a quick status.

Usage:
    python3 scripts/fog-watch.py           # continuous, 60s loop
    python3 scripts/fog-watch.py --once    # single run
    python3 scripts/fog-watch.py --interval 30  # custom interval (seconds)
"""

import sys
import os
import time
import argparse
import json
from datetime import datetime, timezone

WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(WORKSPACE, "scripts"))

# Import from fog-integration (same dir)
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)

# Add fog lib — expand ~ relative to the actual home dir
FOG_LIB = os.path.join(os.path.expanduser("~"), "fog")
sys.path.insert(0, FOG_LIB)

# Rename module file is fog-integration.py (hyphen) — import via importlib
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("fog_integration", os.path.join(SCRIPTS_DIR, "fog-integration.py"))
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
sys.modules["fog_integration"] = _mod

INPUT_PATH = os.path.join(WORKSPACE, "data", "fog", "mesh-snapshot.json")
OUTPUT_PATH = os.path.join(WORKSPACE, "data", "fog", "fog-report.json")
SUMMARY_PATH = os.path.join(WORKSPACE, "data", "fog", "latest-summary.txt")


def run_once(snapshot_path: str) -> bool:
    """Run one fog integration cycle. Returns True on success."""
    if not os.path.exists(snapshot_path):
        print(f"[fog-watch] No snapshot found at {snapshot_path} — waiting for mesh data")
        return False

    try:
        from fog_integration import run_integration, write_report
        report = run_integration(snapshot_path)
        write_report(report, OUTPUT_PATH, SUMMARY_PATH)

        # Print enriched summary with timestamp
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        seam = report.get("seam")
        if seam and seam.get("tension", 0) > 0.7:
            flag = "⚡ HIGH TENSION"
        elif report["mesh"]["dark_core_count"] > 3:
            flag = "🌑 LARGE DARK CORE"
        elif report.get("arbitrage", {}).get("detected"):
            flag = "🔄 ARBITRAGE DETECTED"
        else:
            flag = "✓"

        print(f"[{ts}] {flag} {report['summary']}")
        return True

    except Exception as e:
        print(f"[fog-watch] Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="Sophia fog watcher")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=60, help="Poll interval in seconds (default: 60)")
    parser.add_argument("--snapshot", default=INPUT_PATH, help="Path to mesh-snapshot.json")
    args = parser.parse_args()

    if args.once:
        success = run_once(args.snapshot)
        sys.exit(0 if success else 1)

    print(f"[fog-watch] Starting continuous fog monitoring (interval={args.interval}s)")
    print(f"[fog-watch] Watching: {args.snapshot}")
    print(f"[fog-watch] Output: {OUTPUT_PATH}")
    print(f"[fog-watch] Press Ctrl+C to stop\n")

    while True:
        run_once(args.snapshot)
        try:
            time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n[fog-watch] Stopped.")
            break


if __name__ == "__main__":
    main()
