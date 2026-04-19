#!/usr/bin/env python3
"""
Polymorphic Agent Runner — one process, all Sophia agents, one WebSocket.

Every agent module already exposes handler functions (handle_*). This runner
loads ALL of them, registers their capabilities on a single Agent identity,
subscribes every topic, and keeps the WebSocket alive.

New agents: add an entry to AGENT_DEFS. That's it.

Usage:
    python3 agents/runner.py [--transport ws://localhost:8777] [--persist manifold.db]
    python3 agents/runner.py --list
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import signal
import sys
from pathlib import Path

# Bootstrap Manifold onto path
REPO = Path(__file__).resolve().parent.parent.parent / "repos" / "Manifold"
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.agent import Agent


# ─── Agent Definitions ────────────────────────────────────────────────────────
# Add new agents here. The runner picks them all up.

AGENT_DEFS = {
    "fog-agent": {
        "module": "agents.fog_agent",
        "capabilities": [
            "fog-read",
            "seam-tension",
            "dark-circles",
            "gap-inventory",
            "void-pressure",
            "fog-monitoring",
            "epistemic-cartography",
        ],
        "tasks": {
            "fog/read": "handle_fog_read",
            "fog/seams": "handle_seam_report",
            "fog/dark-circles": "handle_dark_circles",
            "fog/gaps": "handle_gap_inventory",
            "fog/void-pressure": "handle_void_pressure",
        },
    },
    "reach-agent": {
        "module": "agents.reach_agent",
        "capabilities": [
            "reach-scan",
            "reach-pressure",
            "reach-regions",
            "numinous-bridge",
        ],
        "tasks": {
            "reach/scan": "handle_reach_scan",
            "reach/pressure": "handle_reach_pressure",
            "reach/regions": "handle_reach_regions",
        },
    },
    "sentry": {
        "module": "agents.sentry.sentry",
        "capabilities": [
            "mesh-detection",
            "pattern-routing",
            "alert-generation",
            "mesh-monitoring",
        ],
        "tasks": {
            "mesh/scan": "handle_mesh_scan",
            "mesh/alert": "handle_mesh_alert",
        },
    },
    "watchman": {
        "module": "agents.watchman.watchman",
        "capabilities": [
            "detection-modeling",
            "detection-identity",
            "detection-management",
            "detection-solar",
            "detection-strategy",
            "deployment-detection",
            "alert-deployment",
        ],
        "tasks": {
            "watchman/scan": "handle_periodic_scan",
            "watchman/aperture": "handle_aperture_check",
        },
    },
}


# ─── Loader ──────────────────────────────────────────────────────────────────

def _load_handler(module_path: str, handler_name: str):
    mod = importlib.import_module(module_path)
    fn = getattr(mod, handler_name, None)
    if fn is None:
        print(f"  [warn] {module_path} has no function '{handler_name}'", file=sys.stderr)
    return fn


def _make_handler(fn):
    """Wrap a sync or async handler for the subscribe callback."""
    async def wrapper(data: dict):
        try:
            if asyncio.iscoroutinefunction(fn):
                result = await fn(data)
            else:
                result = fn(data)
            return result
        except Exception as e:
            print(f"  [handler error] {fn.__name__}: {e}", file=sys.stderr)
            return {"error": str(e)}
    return wrapper


# ─── Main runner ─────────────────────────────────────────────────────────────

async def run_all(transport: str, persist: str | None, focus: str | None):
    all_capabilities = []
    all_tasks: dict[str, tuple] = {}  # topic → (fn, agent_name)
    loaded_modules: set[str] = set()

    # Collect capabilities and handlers from all defs
    for agent_name, defn in AGENT_DEFS.items():
        module_path = defn["module"]
        capabilities = defn["capabilities"]
        tasks = defn.get("tasks", {})

        all_capabilities.extend(capabilities)

        for topic, handler_name in tasks.items():
            fn = _load_handler(module_path, handler_name)
            if fn is not None:
                all_tasks[topic] = (fn, agent_name)

        # Track loaded modules (avoid double-import noise)
        loaded_modules.add(module_path)

    # Deduplicate capabilities (some may overlap)
    all_capabilities = list(dict.fromkeys(all_capabilities))

    print(f"[poly-runner] {len(AGENT_DEFS)} agents → {len(all_capabilities)} caps → {len(all_tasks)} handlers")

    # Single Agent identity on the mesh
    agent = Agent(
        name="sophia-mesh",
        transport=transport,
        persist_to=persist,
    )
    agent.knows(all_capabilities)
    await agent.join()

    # Subscribe all handlers
    for topic, (fn, agent_name) in all_tasks.items():
        wrapped = _make_handler(fn)
        await agent.subscribe(topic, wrapped)
        print(f"  {topic} ← {agent_name}.{fn.__name__}")

    if focus:
        await agent.think(focus)

    print(f"[sophia-mesh] online | caps={len(all_capabilities)} handlers={len(all_tasks)} transport={transport}")
    print("[sophia-mesh] listening... (ctrl-c to stop)")

    stop = asyncio.Event()
    def _shutdown(*_):
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _shutdown)

    try:
        await stop.wait()
    finally:
        print("\n[sophia-mesh] leaving mesh...")
        await agent.leave()
        print("[sophia-mesh] offline.")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def list_agents():
    for name, defn in AGENT_DEFS.items():
        caps = ", ".join(defn["capabilities"])
        tasks = ", ".join(defn.get("tasks", {}).keys())
        print(f"  {name}: {len(defn['capabilities'])} caps | topics: {tasks}")


def main():
    p = argparse.ArgumentParser(description="Polymorphic runner — all Sophia agents in one process")
    p.add_argument("--transport", default="ws://localhost:8777",
                   help="Transport URI (default: ws://localhost:8777)")
    p.add_argument("--persist", default=None, help="SQLite path for persistent mesh state")
    p.add_argument("--focus", default=None, help="Initial cognitive focus")
    p.add_argument("--list", action="store_true", help="List all registered agents and exit")
    args = p.parse_args()

    if args.list:
        list_agents()
        return

    asyncio.run(run_all(args.transport, args.persist, args.focus))


if __name__ == "__main__":
    main()
