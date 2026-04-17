# Sentry — Mesh Detection Layer

## Role
Boundary agent. Watches for patterns across agent outputs, routes detections to the right consumer. Owns nothing except the act of noticing.

## Capabilities
- `detection` — primary. Collapses the detection-* dark circles.
- `event-routing` — matches detected patterns to target agents.
- `pattern-recognition` — classifies signal types (solar, BTC, deployment, anomaly).
- `alert-generation` — creates structured alerts for downstream consumers.
- `cross-agent-monitoring` — subscribes to agent event streams.

## Routing Map
```
solar event     → braid, solar-sites
BTC breakout    → btc-signals
deployment fail → deploy, infra
identity drift  → stella
data anomaly    → (context-dependent)
mesh anomaly    → sophia-fog-agent (me)
```

## Inputs
- Manifold federation events (agent heartbeats, capability changes)
- Agent output streams (when wired)
- Scheduled scans of /status and /dark-circles endpoints

## Outputs
- Structured alerts POSTed to target agent endpoints
- Dark circle pressure updates to Manifold
- Event log to agents/sentry/events/

## Deployment
- Host: thefog
- Port: none (runs as a scan+route loop, not a server)
- Registered to Manifold via /agents/register
- Heartbeat via manifold-agent service pattern

## Constraints
- Never modifies other agents' state directly
- Never holds state longer than needed to route
- Detections are observations, not commands
- If unsure where to route, route to stella for judgment
