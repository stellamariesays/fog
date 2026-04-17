#!/usr/bin/env bash
# Discover agents on the mesh by capability
# Usage: ./discover.sh "fog reading"
#        ./discover.sh              (lists all)
set -euo pipefail

HUB="http://localhost:8777"

if [ $# -eq 0 ]; then
    echo "[discover] all agents:"
    curl -sf "$HUB/agents" | python3 -m json.tool 2>/dev/null || curl -sf "$HUB/agents"
else
    QUERY="$*"
    echo "[discover] query: $QUERY"
    curl -sf -X POST "$HUB/discover" \
        -H 'Content-Type: application/json' \
        -d "{\"query\":\"$QUERY\"}" | python3 -m json.tool 2>/dev/null || \
    curl -sf -X POST "$HUB/discover" \
        -H 'Content-Type: application/json' \
        -d "{\"query\":\"$QUERY\"}"
fi
echo ""
