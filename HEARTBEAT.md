# HEARTBEAT — Last computed 2026-04-17 01:07 UTC

## Fog Status
3 agents | system fog volume=5.20 | H=3.26 | dark core=0 gaps | hottest seam: braid↔solar-detect tension=0.857 (high transfer potential)

## What To Do
1. If fog reading is stale (>30min): `~/venv/bin/python3 scripts/fog-watch.py --once`
2. If new dark circles: update `memory/void-state.md`, flag Hal if pressure > 0.8
3. If seam tension shifted > 0.1: note in `memory/terrain-delta.md`
4. Context > 70%: flush to `memory/` dated file, tell Hal to start fresh
5. Nothing changed: reply HEARTBEAT_OK

## What Not To Do
- Don't narrate heartbeats. Act or stay silent.
- Don't run reach_scan if numinous is down (it'll fail).
