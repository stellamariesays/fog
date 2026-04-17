#!/usr/bin/env bash
# Sophia mesh agent registration + heartbeat loop
# Registers sophia-fog-agent on the local Manifold hub and heartbeats every 40s
set -euo pipefail

HUB="http://localhost:8777"
AGENT_NAME="sophia-fog-agent"
CAPABILITIES='["fog-reading","dark-circle-detection","reach-analysis","void-pressure","identity-evaluation","reasoning"]'

register() {
    echo "[register] POST $HUB/agents/register → $AGENT_NAME"
    curl -sf -X POST "$HUB/agents/register" \
        -H 'Content-Type: application/json' \
        -d "{\"name\":\"$AGENT_NAME\",\"capabilities\":$CAPABILITIES}" || {
        echo "[register] failed — hub may be down"
        return 1
    }
    echo ""
}

heartbeat() {
    curl -sf -X PUT "$HUB/agents/$AGENT_NAME/heartbeat" -o /dev/null && return 0
    echo "[heartbeat] failed — re-registering"
    register
}

deregister() {
    echo "[deregister] cleaning up $AGENT_NAME"
    curl -sf -X DELETE "$HUB/agents/$AGENT_NAME" -o /dev/null 2>/dev/null || true
    exit 0
}

trap deregister SIGINT SIGTERM

# Initial registration
register || { echo "Cannot reach hub. Exiting."; exit 1; }

# Heartbeat loop
INTERVAL=40
echo "[loop] heartbeating every ${INTERVAL}s (PID $$)"
while true; do
    sleep "$INTERVAL"
    heartbeat
done
