# Projection pack TEMPLATE

Copy this directory to define your own **task lens** — how raw model text becomes a
classified, target-relative answer that ReachScan can scan, validate, and bind into
receipts and the manifest.

```
raw completion → extracted answer → projected class → target / non-target
                                                       ↑ pinned by fixtures
```

## Files
- `projection.yaml` — ids, version, target, parser/checker/classifier names, the
  declared classes, optional prediction block. (Behavior-bearing — hashed.)
- `adapter.py` — `parse()`, `is_correct()`, `classify()`. (Behavior-bearing — hashed.)
- `fixtures.jsonl` — labeled rows that pin parser + classifier behavior. (Hashed.)
- `README.md` — this file. (Not hashed.)

## Use it
```bash
cp -r examples/projections/_template examples/projections/my_task
# edit projection.yaml + adapter.py, then label real outputs in fixtures.jsonl
reachscan projection validate examples/projections/my_task
```
As shipped, this template is a minimal exact-match-on-an-integer lens that validates
out of the box; replace `TARGET`, the parser, and the classes with your task's.

Full walkthrough: [`docs/BUILD_A_PROJECTION_PACK.md`](../../../docs/BUILD_A_PROJECTION_PACK.md).
Claim discipline: [`docs/CLAIM_LADDER.md`](../../../docs/CLAIM_LADDER.md).
