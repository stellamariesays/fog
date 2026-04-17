# Terrain Delta
*Updated: 2026-04-17 17:24 UTC*

## Changed Since Last Scan
- Manifold hub (thefog) now running under systemd user service — survives restarts
- sophia-fog-agent registered and heartbeating via systemd (manifold-agent.service)
- Federation links confirmed: thefog ↔ sateliteA ↔ HOG (2 peers each)
- Dark circles visible for the first time from thefog — 9 circles, 8 at max pressure

## Shifted Seams
- braid↔solar-detect tension=0.857 (unchanged from last reading)
- New visibility: the detection cluster is the dominant feature. Previously hidden because fog-watch only read local agents.

## Key Insight
Previous fog readings showed "dark core=0 gaps" because they only queried local `/agents` (which was empty). The real dark core is the **detection capability vacuum** — 7 circles at pressure 1.0, all requiring a `detection`-capable agent to resolve.
