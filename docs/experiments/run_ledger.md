# ReachScan run ledger

One row per reach-scan run (smoke or full). Fill in **after** each run from
`run_manifest.json` + the printed summary. Keep it honest: record the yield and
the trend, not just the headline number.

> This ledger is an **interpretation layer, not evidence.** Every cell must be
> recomputed from `run_manifest.json` + `receipts.csv`; if prose and raw rows ever
disagree, the raw rows win.

| date | run id | model | revision | GPU | pkg commit | seed | plan (depths × M) | projection | out dir | ok yield (f=0) | R_T trend (f=0 → f=1) | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| _(planned)_ | llama31-floorsum-01 | meta-llama/Llama-3.1-8B-Instruct | _TBD@run_ | _TBD_ | _TBD_ | 0 | 0/.25/.5/.75/.9/1 × 128/64/64/128/128/128 | floor_sum_mod8 (primary); floor_sum_exact sanity | examples/openweights_floor_sum/artifacts | — | — | predeclared — see docs/experiments/llama31_floor_sum_predeclared.md |

Column notes:
- **revision** — exact model commit SHA (pin it; don't float to latest).
- **pkg commit** — the reachscan git commit installed for the run.
- **ok yield (f=0)** — `ok_answers / attempts` at the prompt-only state; if low,
  the run is untrustworthy for R_T (extractor/format problem, not reachability).
- **R_T trend** — e.g. `0.41 → 0.05 (sustained fall)` or `flat` or `noisy`.
