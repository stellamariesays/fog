#!/usr/bin/env bash
# Sentry agent registration + heartbeat to Manifold
set -euo pipefail

HUB="http://localhost:8777"
AGENT_NAME="sentry"
CAPABILITIES='["detection","event-routing","pattern-recognition","alert-generation","cross-agent-monitoring"]'

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

register || { echo "Cannot reach hub. Exiting."; exit 1; }

INTERVAL=40
echo "[loop] heartbeating every ${INTERVAL}s (PID $$)"
while true; do
    sleep "$INTERVAL"
    heartbeat
done
