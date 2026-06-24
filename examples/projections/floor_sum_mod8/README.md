# floor_sum_mod8 — projection pack

The first formal **projection pack**: a task-specific answer lens declared
precisely enough that ReachScan can run, validate, and bind it into receipts and
the manifest. It is the floor-sum flagship (correct answer 532; `532 % 8 == 4`)
expressed as the spec's pack format.

## Files (behavior-bearing files are hashed)
- `projection.yaml` — ids, version, target, parser/checker/classifier names, the
  declared classes, the predeclared prediction block, exposure policy.
- `adapter.py` — `parse()`, `is_correct()`, `classify()`. Self-contained.
- `fixtures.jsonl` — labeled rows that pin parser + classifier behavior.
- `README.md` — this file (NOT hashed).

The `projection_pack_hash` covers `projection.yaml` + `adapter.py` +
`fixtures.jsonl` (path + bytes). Change any of them and the pack identity changes —
a parser edit can never keep the same hash.

## Declared classes
`residue_0 … residue_7`, `no_answer`, `invalid`. The **target class** is
`residue_4`.

> Note the deliberate gap between the **outcome check** and the **projection
> class**: `540` and `916` are in `residue_4` (the target *class*) but are **not**
> the correct answer 532 (`is_correct` is False). The projection class is a residue
> fiber, not the exact answer. `target_hit` in receipts is the exact outcome check;
> the engine's target reachability is mass on the target *class*.

## Validate
```bash
reachscan projection validate examples/projections/floor_sum_mod8
```
This loads the pack, runs the fixtures through the adapter, and prints the
`projection_pack_hash`. Fixtures must pass before a claim-bearing run.

## Evaluate the predeclared prediction (v0.3.1)
After a pack-driven run, compute the morphology verdict from raw receipts:
```bash
reachscan prediction evaluate <run_dir> --projection examples/projections/floor_sum_mod8
```
This writes `prediction_verdict.json` (`supported / failed / inconclusive`) and
records the prediction block in `run_manifest.json`. The run must have used THIS
pack (the evaluator checks the `projection_pack_hash`). `run_pack_demo.py` produces
a suitable mock run.

## Status
This pack is at claim level `morphology_demo`. Real answer-exposure auditing and
claim levels above `morphology_demo` remain future work.
