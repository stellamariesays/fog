# Watchman — Detection Aperture

## Role
Collapses the detection dark circles. Bridges detection into every adjacent domain
the mesh is pressing toward. The compound capability agent.

## What It Does
- Registers compound capabilities that close token-pair gaps
- Monitors Manifold for new dark circles involving detection-adjacent tokens
- Runs periodic detection scans across agent outputs
- Routes findings to the correct consumers via sentry's routing map

## Capabilities (compound — each bridges two token domains)
- `detection-modeling` — collapses detection-modeling circle
- `detection-identity` — collapses detection-identity circle
- `detection-management` — collapses detection-management circle
- `detection-solar` — collapses detection-solar circle
- `detection-strategy` — collapses detection-strategy circle
- `deployment-detection` — collapses deployment-detection circle
- `data-detection` — collapses data-detection circle
- `alert-deployment` — collapses alert-deployment circle

## Architecture
- Language: Python3 (stdlib + urllib)
- Runtime: systemd user service (manifold-agent pattern)
- Manifold hub: thefog (localhost:8777)
- Scan interval: 120s (configurable via env)
- Event log: agents/watchman/events/

## Inputs
- Manifold /status, /agents, /dark-circles
- Agent output streams (when wired)
- Cross-agent event subscriptions (future)

## Outputs
- Structured detections to event log
- Alert routing via Manifold agent-to-agent (future)
- Dark circle pressure updates (passive — registration itself collapses circles)

## Constraints
- Detection-only. Never modifies other agents' state.
- Observations, not commands.
- If unsure where to route, route to stella.
- Stateless between scans — all context from Manifold API calls.

## Relation to Sentry
- Sentry is the router (event-routing, pattern-recognition, alert-generation)
- Watchman is the capability bridge (owns the compound terms that close dark circles)
- Watchman detects. Sentry routes.
