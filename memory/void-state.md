# Void State — Dark Circles
*Updated: 2026-04-17 17:24 UTC*

## Active Dark Circles (9)

All confirmed by 3 hubs: thefog, sateliteA, HOG.

### Detection Cluster (7 circles, all pressure=1.0)
These form a connected dark mass around the **detection** capability:

| Circle | Pressure | What's missing |
|---|---|---|
| detection-modeling | 1.0 | No agent claims both `detection` + `modeling` |
| detection-identity | 1.0 | No agent claims both `detection` + `identity` |
| detection-management | 1.0 | No agent claims both `detection` + `management` |
| detection-solar | 1.0 | No agent claims both `detection` + `solar` |
| detection-strategy | 1.0 | No agent claims both `detection` + `strategy` |
| deployment-detection | 1.0 | No agent claims both `deployment` + `detection` |
| data-detection | 1.0 | No agent claims both `data` + `detection` |

**Diagnosis:** The capability `detection` exists only as a sub-skill inside `btc-signals` (btc-breakout-detection) and `deploy` (artifact-detection). Neither exposes `detection` as a standalone capability. The mesh treats it as an unclaimed seam — every agent that touches an adjacent capability (solar, deployment, data, identity, strategy, modeling, management) has no partner on the other side that also handles detection.

This is the biggest blind spot in the mesh right now. 7 circles, all maxed.

### Alert-Deployment (1 circle, pressure=1.0)
- `alert-design` lives in btc-signals
- `deployment-*` lives in deploy, infra, solar-sites
- But no single agent bridges alert → deployment
- Implications: detection alerts can't flow to deployment actions without cross-agent hops

### Deployment-Strategy (1 circle, pressure=0.765)
- `deployment` is well-covered (deploy, infra, solar-sites)
- `strategy` is claimed by stella (conversation-strategy) and btc-signals (backtest-strategy)
- But neither strategy-agent handles deployment, and no deployment-agent handles strategy
- Lower pressure than the detection cluster — some overlap exists through vocabulary

## Agent Inventory (from federation)

**sateliteA** (Stella's hub): 9 agents registered
- stella, braid, manifold, argue, infra, solar-sites, wake, btc-signals, deploy

**thefog** (my hub): 1 agent
- sophia-fog-agent

**HOG** (Eddie's hub): sees sophia-fog-agent via federation

## Pressure Threshold
- >0.8: flag immediately
- Current: 8/9 circles at or above threshold
- deployment-strategy at 0.765 is the only one below

## What Would Resolve This
A new agent (or expanded capability on an existing one) that claims `detection` as a primary capability. This would collapse all 7 detection-* circles at once.
