# Build a projection pack — porting the *interpretation*, not just the engine

ReachScan's engine is task-agnostic: it freezes a committed prefix, samples
futures, and tallies a field. What makes a scan *mean* something is the
**projection** — the lens that turns raw model text into a classified,
target-relative answer. The engine ports for free; the lens is what you bring.

A **projection pack** makes that lens declared, fixture-validated, and hashed, so a
scan on your task is as auditable as the flagship. This guide is how to build one.

## The pipeline you are defining

```
raw completion ──parse──▶ extracted answer ──classify──▶ projected class ──▶ target / non-target
                                                                              ▲
                                                            fixtures pin every step
```

## Five decisions

1. **Answer space** — what *kind* of answer is it? (integer, string, multiple
   choice, a program's output…). Sets `answer_space_type`.
2. **Parser** (`parse`) — pull the terminal answer from raw text; return `None`
   when there is none. This is brittle *by design* — make it explicit, not clever.
3. **Target** (`is_correct`) — the **outcome check**: did the answer hit the
   correct endpoint? (e.g. exactly `532`.)
4. **Classes** (`classify`) — map every answer to one **predeclared** class,
   including `no_answer` and `invalid`. One class is the `target_class`.
5. **Fixtures** — labeled rows (`raw_text`, `parsed_answer`, `target_hit`,
   `projection_class`) that pin parser + classifier behavior. Draw them from
   **real or representative outputs**, declared *before* you scan.

## The binding rule (don't skip this)

`is_target` must be a **property of the `project()` class**: if two answers share a
class, they share the same target membership. The engine enforces this — a class
that holds both target and non-target answers fails loud.

This is also why **outcome ≠ target class**. In the floor-sum flagship the target
*class* is the residue fiber `residue_4` (which contains 532 — and also 540, 916…),
while the **outcome check** is exactly 532. `target_hit` in receipts is the exact
outcome; target reachability is mass on the target *class*. Keep the two straight:
your class scheme is the morphology lens; your outcome check is correctness.

## Steps

```bash
cp -r examples/projections/_template examples/projections/my_task
```
1. In `projection.yaml`: set `projection_id`, `task_family`, `answer_space_type`,
   `target`, the `classes` list, and `target_class`. Set `claim_level` honestly
   (see [`CLAIM_LADDER.md`](CLAIM_LADDER.md)).
2. In `adapter.py`: write `parse`, `is_correct`, `classify`. Every string
   `classify` can return must appear in `classes`.
3. In `fixtures.jsonl`: label representative outputs — at least the target, a
   wrong answer, and a no-answer; cover each class you expect.
4. Validate:
   ```bash
   reachscan projection validate examples/projections/my_task
   ```
   Fixtures must pass before any claim-bearing run; an undeclared emitted class is
   a hard error.
5. Run with it (the pack satisfies the engine `Projection` protocol, so the
   notebook / `reach_scan` use it directly). Receipts then carry `projection_class`
   + the pack identity; the manifest carries the `projection_pack` block.

## Behavior-bearing identity

The `projection_pack_hash` covers `projection.yaml` + `adapter.py` +
`fixtures.jsonl` (path + bytes). Edit the parser and the identity changes — a lens
cannot drift while claiming the same hash. Record the hash with your run.

## Optional: make it claim-bearing

Add a `prediction` block (commented stub in the template) to predeclare the
morphology test, then evaluate it from receipts:
```bash
reachscan prediction evaluate <run_dir> --projection examples/projections/my_task
```
See [`PREDICTION_CONTRACT.md`](PREDICTION_CONTRACT.md).

## Honesty

- **Predeclare classes and thresholds.** Inventing a class or tuning a threshold
  *after* seeing outputs is the cardinal leakage; the hash exists to prevent it.
- **Fixtures are not cherry-picks.** They should represent the model's real output
  distribution, or they validate a lens that doesn't match reality.
- Porting a lens to a new task is a new measurement, not generality — place it on
  the [claim ladder](CLAIM_LADDER.md) by how the run was designed.
