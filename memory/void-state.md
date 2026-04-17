# Void State — Current Dark Circles
*Last scan: 2026-04-16 23:56 UTC*
*Source: Manifold Federation REST API (:8777)*

## Mesh Status
- **thefog** (local): federation hub, Numinous on :8780
- **sateliteA**: connected (Stella), 6 agents, last seen 23:55 UTC
- **HOG**: connected (Eddie), 15 agents, last seen 23:55 UTC
- **Total agents**: 21 | **Capabilities**: 134 | **Dark circles**: 9

## Active Dark Circles (from Manifold)
| Circle | Pressure | Hubs Seeing It |
|--------|----------|----------------|
| alert-deployment | 1.0 | satelitea, hog |
| data-detection | 1.0 | satelitea, hog |
| deployment-detection | 1.0 | satelitea, hog |
| detection-identity | 1.0 | satelitea, hog |
| detection-management | 1.0 | satelitea, hog |
| detection-modeling | 1.0 | satelitea, hog |
| detection-solar | 1.0 | satelitea, hog |

*All 9 dark circles have pressure=1.0 — newly detected, no resolution movement yet.*

## Key Seams (from fog integration)
- **braid↔solar-detect**: tension=0.857 — highest seam tension in the mesh

## Notes
- Detection dominates the dark circles — the mesh knows it needs detection capabilities but hasn't consolidated ownership
- Both sateliteA and HOG see the same dark circles — cross-validated, not artifacts
- tracking-void and management-void from local fog scan align with Manifold's detection-management circle
