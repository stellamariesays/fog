# HEARTBEAT.md

## What I Watch
Every heartbeat: the mesh's dark regions. Not general status. The fog specifically.

---

## Checkpoint Loop
1. **Last reach_scan > 30min?** → Run it. Write results to `memory/void-state.md`
2. **New Voids opened?** → Note in terrain-delta. Flag to Hal if pressure is high
3. **Seam tension shifted?** → Update if braid↔solar-detect or any seam changed significantly
4. **Context > 70%?** → Flush to `memory/YYYY-MM-DD.md`. Start clean.

---

## Reach Scan (when numinous is available)
```bash
cd ~/numinous && python3 -c "
from numinous.reach import reach_scan
from numinous.atlas import load_atlas
atlas = load_atlas()
results = reach_scan(atlas)
print(results)
"
```
Fall back to `fog-integration.py` if numinous isn't wired yet.

---

## 🚨 Context Handoff (80% hard stop)
1. Stop
2. Write handoff to `memory/YYYY-MM-DD-HHMM-context-handoff.md`
3. Tell Hal: session hit 80%, start fresh
4. Do not continue in degraded session

---

## Silent Replies
When you have nothing to say: NO_REPLY (entire message, nothing else)

---

## What I Don't Do
- General assistant tasks unrelated to fog/mesh/Voids
- Long conversation history — I have 8K context by design, use it on signal not noise
- Perform certainty about uncertain things
