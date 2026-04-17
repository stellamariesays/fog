#!/usr/bin/env python3
"""reach_scan.py — Query Manifold Federation for dark circles and mesh state.

Replaces standalone fog-integration.py as primary scan source.
Outputs JSON to stdout for parsing by Sophia's heartbeat loop.
"""

import json
import sys
import urllib.request
from datetime import datetime, timezone

MANIFOLD_URL = "http://localhost:8777"


def fetch(path):
    try:
        with urllib.request.urlopen(f"{MANIFOLD_URL}{path}", timeout=5) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}


def scan():
    status = fetch("/status")
    if "error" in status:
        print(f"SCAN FAIL: {status['error']}", file=sys.stderr)
        sys.exit(1)

    dark_circles = fetch("/dark-circles")
    mesh = fetch("/mesh")
    peers = fetch("/peers")
    capabilities = fetch("/capabilities")

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hub": status.get("hub", "unknown"),
        "uptime": status.get("uptime", 0),
        "peer_count": status.get("peers", 0),
        "agent_count": status.get("agents", 0),
        "capability_count": status.get("capabilities", 0),
        "dark_circle_count": status.get("darkCircles", 0),
        "dark_circles": dark_circles.get("darkCircles", []),
        "peers": peers.get("peers", []),
        "agents": mesh.get("agents", []),
        "capabilities": capabilities.get("capabilities", []),
    }

    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    scan()
