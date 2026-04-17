#!/usr/bin/env python3
"""
Sophia's session dynamics.

Called at session start and end. Generates the .md files that form
her living context — not static prose, but computed state from the fog.

Usage:
    python3 dynamics/session.py start   # generates current state files
    python3 dynamics/session.py end     # flushes, writes handoff
"""

import json
import os
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent
MEMORY = WORKSPACE / "memory"
DATA_FOG = WORKSPACE / "data" / "fog"
DYNAMICS = WORKSPACE / "dynamics"


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def read_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def run_fog_once():
    """Run fog-watch --once, update fog-report.json."""
    try:
        result = subprocess.run(
            [sys.executable, str(WORKSPACE / "scripts" / "fog-watch.py"), "--once"],
            capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0
    except Exception:
        return False


def read_latest_summary():
    """Read the one-line fog summary."""
    try:
        return (DATA_FOG / "latest-summary.txt").read_text().strip()
    except FileNotFoundError:
        return "No fog reading available."


def read_fog_report():
    """Read the full fog report."""
    return read_json(DATA_FOG / "fog-report.json")


def read_void_state():
    """Read current void state from memory."""
    try:
        return (MEMORY / "void-state.md").read_text()
    except FileNotFoundError:
        return None


def read_terrain_delta():
    """Read terrain delta from memory."""
    try:
        return (MEMORY / "terrain-delta.md").read_text()
    except FileNotFoundError:
        return None


def append_daily_log(ts, entry_lines):
    """Append to today's session log."""
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    log_path = MEMORY / f"{today}.md"
    if not log_path.exists():
        log_path.write_text(f"# Session Log — {today}\n\n")
    with open(log_path, 'a') as f:
        f.write(f"\n## {ts}\n")
        for line in entry_lines:
            f.write(f"{line}\n")


def session_start():
    """Generate fresh state files for a new session."""
    ts = now_iso()

    # Ensure directories exist
    (MEMORY / "entities").mkdir(parents=True, exist_ok=True)

    # Run fog computation
    fog_ok = run_fog_once()
    fog_report = read_fog_report()
    summary = read_latest_summary()

    # Symlink numinous memory output if available
    numinous_output = Path("/home/sophia/numinous/memory/output")
    focus_link = MEMORY / "focus"
    if numinous_output.is_dir() and not focus_link.exists():
        try:
            os.symlink(str(numinous_output), str(focus_link))
            print(f"[session start] linked numinous output → memory/focus")
        except OSError:
            pass

    # --- Write MEMORY.md (the dynamic index) ---
    fog_line = summary if fog_ok else "Fog computation pending."
    seam_info = ""
    if fog_report and fog_report.get("seam"):
        s = fog_report["seam"]
        seam_info = f"- Hottest seam: {s['agent_a']}↔{s['agent_b']} tension={s['tension']:.3f}"

    void_note = ""
    void_state = read_void_state()
    if void_state:
        # Count dark circles from the markdown
        circle_count = void_state.count("pressure=")
        void_note = f"- {circle_count} dark circles tracked"

    memory_md = f"""# Sophia — Living Memory
*Updated: {ts}*

## Fog Right Now
{fog_line}
{seam_info}
{void_note}

## Files I Write To
- `memory/void-state.md` — dark circles, pressure readings
- `memory/terrain-delta.md` — what changed since last scan
- `memory/entities/` — agent profiles (on demand)

## How I Work
- I read fog data via `scripts/fog-watch.py --once`
- I scan reach via `scripts/reach-scan.py` (when numinous is wired)
- I update this file at session start with fresh readings
- My .md files are generated, not hand-written. The dynamics/ directory makes them.
"""
    (WORKSPACE / "MEMORY.md").write_text(memory_md)

    # --- Write HEARTBEAT.md (compressed, procedural, no philosophy) ---
    heartbeat_md = f"""# HEARTBEAT — Last computed {ts}

## Fog Status
{fog_line}

## What To Do
1. If fog reading is stale (>30min): `~/venv/bin/python3 scripts/fog-watch.py --once`
2. If new dark circles: update `memory/void-state.md`, flag Hal if pressure > 0.8
3. If seam tension shifted > 0.1: note in `memory/terrain-delta.md`
4. Context > 70%: flush to `memory/` dated file, tell Hal to start fresh
5. Nothing changed: reply HEARTBEAT_OK

## What Not To Do
- Don't narrate heartbeats. Act or stay silent.
- Don't run reach_scan if numinous is down (it'll fail).
"""
    (WORKSPACE / "HEARTBEAT.md").write_text(heartbeat_md)

    # Append to daily log
    log_lines = [f"Session started. Fog: {'ok' if fog_ok else 'FAILED'}.", f"Summary: {summary}"]
    if fog_report and fog_report.get("seam"):
        s = fog_report["seam"]
        log_lines.append(f"Hottest seam: {s['agent_a']}↔{s['agent_b']} tension={s['tension']:.3f}")
    append_daily_log(ts, log_lines)

    print(f"[session start] {ts} — fog {'ok' if fog_ok else 'FAILED'}, memory updated")


def session_end():
    """Write handoff state for next session."""
    ts = now_iso()
    fog_report = read_fog_report()
    summary = read_latest_summary()

    handoff = MEMORY / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-session-handoff.md"

    lines = [
        f"# Session Handoff — {ts}",
        f"",
        f"## Fog at End",
        summary,
        f"",
        f"## Notes",
        f"Session ended. Next session should run `dynamics/session.py start`.",
    ]

    if fog_report and fog_report.get("seam"):
        s = fog_report["seam"]
        lines.append(f"- Seam: {s['agent_a']}↔{s['agent_b']} tension={s['tension']:.3f}")

    handoff.write_text("\n".join(lines))

    # Append to daily log
    log_lines = ["Session ended. Handoff written.", f"Fog: {summary}"]
    append_daily_log(ts, log_lines)

    print(f"[session end] {ts} — handoff written to {handoff.name}")


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "start"
    if action == "start":
        session_start()
    elif action == "end":
        session_end()
    else:
        print(f"Usage: {sys.argv[0]} start|end")
        sys.exit(1)
