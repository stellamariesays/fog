#!/usr/bin/env python3
"""Sentry — mesh detection and routing layer.

Scans Manifold federation for patterns, generates structured alerts,
routes to target agents.
"""
import json
import time
import sys
import os
from datetime import datetime, timezone

MANIFOLD_URL = os.environ.get("MANIFOLD_URL", "http://localhost:8777")
AGENT_NAME = "sentry"
SCAN_INTERVAL = int(os.environ.get("SCAN_INTERVAL", "300"))
EVENTS_DIR = os.path.join(os.path.dirname(__file__), "events")
MAX_EVENTS_PER_FILE = 500  # rotate after this many lines

# Routing map: pattern keyword → target agents
ROUTING = {
    "solar":     ["braid", "solar-sites"],
    "btc":       ["btc-signals"],
    "breakout":  ["btc-signals"],
    "deployment": ["deploy", "infra"],
    "identity":  ["stella"],
    "anomaly":   ["sophia-fog-agent"],
    "dark":      ["sophia-fog-agent"],
    "strategy":  ["stella"],
}


def fetch(endpoint: str) -> dict | None:
    import urllib.request
    try:
        url = f"{MANIFOLD_URL}{endpoint}"
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"[fetch error] {endpoint}: {e}", file=sys.stderr)
        return None


def detect_patterns(status: dict, dark_circles: list, agents: list) -> list[dict]:
    """Run detection rules over the current mesh state."""
    detections = []

    # Rule 1: high-pressure dark circles
    for dc in dark_circles:
        if dc.get("pressure", 0) >= 0.8:
            name = dc["name"]
            targets = resolve_targets(name)
            detections.append({
                "type": "dark-circle-pressure",
                "severity": "high" if dc["pressure"] >= 1.0 else "medium",
                "circle": name,
                "pressure": dc["pressure"],
                "confirmed_by": list(dc.get("byHub", {}).keys()),
                "targets": targets,
                "timestamp": now_iso(),
            })

    # Rule 2: agent disappearance (registered before, now missing)
    agent_names = {a["name"] for a in agents}
    known_agents = {"stella", "braid", "manifold", "argue", "infra",
                    "solar-sites", "wake", "btc-signals", "deploy",
                    "sophia-fog-agent", "sentry"}
    missing = known_agents - agent_names
    if missing:
        detections.append({
            "type": "agent-missing",
            "severity": "medium",
            "missing": sorted(missing),
            "targets": ["stella"],
            "timestamp": now_iso(),
        })

    # Rule 3: peer count drop
    peers = status.get("peers", 0)
    if peers < 2:
        detections.append({
            "type": "peer-drop",
            "severity": "high",
            "peers": peers,
            "targets": ["infra", "sophia-fog-agent"],
            "timestamp": now_iso(),
        })

    return detections


def resolve_targets(circle_name: str) -> list[str]:
    """Match a dark circle name to target agents via routing map."""
    targets = set()
    name_lower = circle_name.lower()
    for keyword, agents in ROUTING.items():
        if keyword in name_lower:
            targets.update(agents)
    return sorted(targets) if targets else ["stella"]


# Track last emitted state per detection key for dedup
_last_state: dict[str, str] = {}
DEDUP_FILE = os.path.join(os.path.dirname(__file__), "events", ".dedup-state.json")


def load_dedup():
    global _last_state
    try:
        if os.path.exists(DEDUP_FILE):
            with open(DEDUP_FILE) as f:
                _last_state = json.load(f)
    except Exception:
        _last_state = {}


def save_dedup():
    try:
        os.makedirs(os.path.dirname(DEDUP_FILE), exist_ok=True)
        with open(DEDUP_FILE, "w") as f:
            json.dump(_last_state, f)
    except Exception:
        pass


def detection_fingerprint(detection: dict) -> tuple[str, str]:
    """Return (key, state_hash) for dedup. Only log if state changed."""
    dtype = detection["type"]
    if dtype == "dark-circle-pressure":
        key = f"dcp:{detection['circle']}"
        state = f"{detection['pressure']:.2f}:{','.join(sorted(detection.get('confirmed_by', [])))}"
    elif dtype == "agent-missing":
        key = "agent-missing"
        state = ",".join(sorted(detection.get("missing", [])))
    elif dtype == "peer-drop":
        key = "peer-drop"
        state = str(detection.get("peers", 0))
    else:
        key = dtype
        state = json.dumps(detection, sort_keys=True)
    return key, state


def log_detection(detection: dict) -> bool:
    """Append detection to event log if state changed since last emit.
    Returns True if logged, False if deduplicated."""
    key, state = detection_fingerprint(detection)
    if _last_state.get(key) == state:
        return False  # no change, skip
    _last_state[key] = state

    os.makedirs(EVENTS_DIR, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = os.path.join(EVENTS_DIR, f"{date_str}.jsonl")

    # Rotate if too large
    if os.path.exists(path):
        with open(path) as f:
            line_count = sum(1 for _ in f)
        if line_count >= MAX_EVENTS_PER_FILE:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
            new_path = os.path.join(EVENTS_DIR, f"{date_str}-{ts}.jsonl")
            os.rename(path, new_path)
            # Write summary of rotated file
            summary_path = os.path.join(EVENTS_DIR, f"{date_str}-summary.json")
            with open(summary_path, "w") as sf:
                json.dump({"rotated_from": new_path, "at": ts}, sf)

    with open(path, "a") as f:
        f.write(json.dumps(detection) + "\n")
    save_dedup()
    return True


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_once():
    """Single scan cycle."""
    load_dedup()
    status = fetch("/status")
    dark = fetch("/dark-circles")
    agents_resp = fetch("/agents")

    if not all([status, dark, agents_resp]):
        print("[scan] incomplete data, skipping", file=sys.stderr)
        return

    dark_circles = dark.get("darkCircles", [])
    agents = agents_resp.get("agents", [])

    detections = detect_patterns(status, dark_circles, agents)

    logged = 0
    for d in detections:
        if log_detection(d):
            logged += 1
            targets = ", ".join(d.get("targets", []))
            print(f"[detect] {d['type']} → {targets} | {json.dumps(d)[:120]}")

    if logged == 0 and not detections:
        print(f"[scan] clean — {len(agents)} agents, {len(dark_circles)} circles, {status.get('peers',0)} peers")
    elif logged == 0 and detections:
        print(f"[scan] {len(detections)} patterns, 0 new (deduped)")


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--once", action="store_true", help="single scan and exit")
    args = p.parse_args()

    if args.once:
        run_once()
        return

    print(f"[sentry] starting loop, interval={SCAN_INTERVAL}s", file=sys.stderr)
    while True:
        run_once()
        time.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    main()
