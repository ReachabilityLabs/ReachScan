# Prediction contract (v0.3.1) — the morphology verdict

A projection pack declares the **lens** (parser, classes, target). Its
`prediction` block declares the **test**: what wrong-answer morphology would count
as `supported`, `failed`, or `inconclusive` — *before* the run. After the run,
`reachscan prediction evaluate` computes the verdict mechanically from the **raw
receipts**, so morphology is a declared measurement rather than a post-hoc story.

It is a layer over the engine: it reads receipts and a pack; it does not change
the measurement.

## What is tested

The tests read the **wrong-answer field** over the declared projection classes
(not target foreclosure). Wrong = `target_hit` False (the exact outcome check) and
`parse_status == "ok"`; the target class and `no_answer`/`invalid` are excluded
from the structural class set.

| test type | question | rule |
|---|---|---|
| `family_structure` | do wrong answers concentrate into declared families, or spread like noise? | normalized entropy over structural classes vs `max_entropy`/`min_entropy`, dispatched by `expected_mode` (`concentrated` / `diffuse` / `mixed`) |
| `morphology_mode` | capture, shatter, or mixed? | entropy ≤ `capture_max` → capture; ≥ `shatter_min` → shatter; between → mixed |
| `family_before_atom` | did the family grain collapse before any single atom (exact answer) won? | family grain = `projection_class`, atom grain = `parsed_answer`; masses are scored over parsed (ok) answers only, each usable depth needs `min_n_per_depth` ok answers, and the first usable depth must have a viable target mass |

Run verdict (`loss_rule: any_test_failed`, the only accepted rule):

```
failed        if ANY test failed
inconclusive  elif ANY test inconclusive
supported     else
```

`inconclusive` is load-bearing: too few structural wrong answers (`min_n`), a
missing depth band, a target already collapsed before the first usable depth, an
unknown test type, or an unsupported loss rule all yield `inconclusive` — never a
false `supported`/`failed`. In particular, because `family_before_atom` scores
over parsed (ok) answers and requires `min_n_per_depth` of them per depth, a depth
where extraction failed (all `no_answer`/`invalid`) cannot read as a family
collapse — yield failure is not morphology.

## Honesty + anti-post-hoc locks

- **Predeclared + hashed.** The `prediction` block is hashed with the pack
  (`projection.yaml` is behavior-bearing) and separately as `prediction_hash`; the
  thresholds cannot be tuned after seeing the data without changing the hash.
- **Projection lock.** The evaluator refuses a run whose
  `projection_pack_hash` does not match the pack — no swapping the lens after the
  fact.
- **Source arms.** `applies_to.source_arm` filters receipts to one declared arm so
  prompt-only / correct-source / wrong-source rows are not silently mixed.
- **Raw receipts only.** The verdict is computed from `receipts.csv`, not a summary.

## Use

```bash
# after a pack-driven run (see examples/projections/floor_sum_mod8/run_pack_demo.py)
reachscan prediction evaluate <run_dir> --projection examples/projections/floor_sum_mod8
```

Writes `prediction_verdict.json` (outcome, `prediction_hash`, per-test detail,
honesty notes) and records a `prediction` block (hash, tests, verdict path,
outcome) in `run_manifest.json`.

## Deferred

- Real answer-exposure auditing + claim levels above `morphology_demo` (the
  `bounded_scientific_measurement`+ tiers require the exposure ledger).
- Bootstrap/permutation intervals replacing fixed entropy cutoffs (same artifact
  shape, sharper internals).
