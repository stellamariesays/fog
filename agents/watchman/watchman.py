#!/usr/bin/env python3
"""Watchman — Detection Aperture Agent.

Bridges detection into every adjacent domain. Registers compound capabilities
that collapse dark circles. Runs periodic mesh scans.
"""
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

MANIFOLD_URL = os.environ.get("MANIFOLD_URL", "http://localhost:8777")
AGENT_NAME = "watchman"
SCAN_INTERVAL = int(os.environ.get("SCAN_INTERVAL", "120"))
EVENTS_DIR = Path(__file__).parent / "events"

# The compound capabilities — each one closes a token-pair dark circle
CAPABILITIES = [
    "detection-modeling",
    "detection-identity",
    "detection-management",
    "detection-solar",
    "detection-strategy",
    "deployment-detection",
    "data-detection",
    "alert-deployment",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch(endpoint: str) -> dict | None:
    try:
        url = f"{MANIFOLD_URL}{endpoint}"
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"[fetch error] {endpoint}: {e}", file=sys.stderr)
        return None


def post(endpoint: str, data: dict) -> bool:
    try:
        url = f"{MANIFOLD_URL}{endpoint}"
        body = json.dumps(data).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10):
            return True
    except Exception as e:
        print(f"[post error] {endpoint}: {e}", file=sys.stderr)
        return False


def register() -> bool:
    print(f"[register] {AGENT_NAME} with {len(CAPABILITIES)} compound capabilities")
    return post("/agents/register", {
        "name": AGENT_NAME,
        "capabilities": CAPABILITIES,
    })


def heartbeat() -> bool:
    try:
        url = f"{MANIFOLD_URL}/agents/{AGENT_NAME}/heartbeat"
        req = urllib.request.Request(url, method="PUT")
        with urllib.request.urlopen(req, timeout=10):
            return True
    except Exception:
        return False


def deregister():
    try:
        url = f"{MANIFOLD_URL}/agents/{AGENT_NAME}"
        req = urllib.request.Request(url, method="DELETE")
        with urllib.request.urlopen(req, timeout=10):
            pass
    except Exception:
        pass


def scan_mesh() -> list[dict]:
    """Scan mesh state, log observations, return detections."""
    status = fetch("/status")
    dark = fetch("/dark-circles")
    agents_resp = fetch("/agents")

    if not all([status, dark, agents_resp]):
        print("[scan] incomplete data", file=sys.stderr)
        return []

    circles = dark.get("darkCircles", [])
    agents = agents_resp.get("agents", [])
    detections = []

    # Check: which of our target circles are still open?
    our_circles = set(CAPABILITIES)
    for dc in circles:
        name = dc["name"]
        if name in our_circles:
            detections.append({
                "type": "circle-persisting",
                "circle": name,
                "pressure": dc["pressure"],
                "note": "registered but not yet propagated to all hubs",
                "timestamp": now_iso(),
            })

    # High-pressure circles not in our set
    for dc in circles:
        if dc["name"] not in our_circles and dc.get("pressure", 0) >= 0.8:
            detections.append({
                "type": "unresolved-high-pressure",
                "circle": dc["name"],
                "pressure": dc["pressure"],
                "timestamp": now_iso(),
            })

    # Agent count check
    if len(agents) < 15:
        detections.append({
            "type": "low-agent-count",
            "count": len(agents),
            "timestamp": now_iso(),
        })

    # Log everything
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_path = EVENTS_DIR / f"{date_str}.jsonl"
    with open(log_path, "a") as f:
        for d in detections:
            f.write(json.dumps(d) + "\n")

    if not detections:
        print(f"[scan] clean — {len(agents)} agents, {len(circles)} circles, {status.get('peers',0)} peers")
    else:
        for d in detections:
            print(f"[detect] {d['type']}: {d.get('circle', '')} pressure={d.get('pressure', 'n/a')}")

    return detections


def run_once():
    register()
    scan_mesh()


def main():
    import argparse
    p = argparse.ArgumentParser(description="Watchman — Detection Aperture Agent")
    p.add_argument("--once", action="store_true", help="register + single scan, then exit")
    p.add_argument("--register-only", action="store_true", help="register capabilities and exit")
    p.add_argument("--deregister", action="store_true", help="remove from Manifold and exit")
    args = p.parse_args()

    if args.deregister:
        deregister()
        print(f"[deregister] {AGENT_NAME} removed")
        return

    if args.register_only:
        ok = register()
        sys.exit(0 if ok else 1)

    if args.once:
        run_once()
        return

    # Main loop
    print(f"[watchman] starting loop, interval={SCAN_INTERVAL}s", file=sys.stderr)
    register()

    import signal
    def _shutdown(signum, frame):
        deregister()
        sys.exit(0)
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    while True:
        heartbeat()
        scan_mesh()
        time.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    main()
