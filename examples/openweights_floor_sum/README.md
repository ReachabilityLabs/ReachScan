# Open-weights floor-sum example (Llama-3.1-8B-Instruct)

**Status: scaffold (pre-run).** No model artifacts yet — this folder fills in
after the real run.

This is the planned first **cross-model** worked example: ReachScan on
`meta-llama/Llama-3.1-8B-Instruct`, the same floor-sum task as the flagship,
measuring exact-target reachability (`ExactMatch(532)`) as a committed prefix
deepens. It doubles as a template for running the instrument on *your own*
open-weights model.

Locked design: [`docs/experiments/llama31_floor_sum_predeclared.md`](../../docs/experiments/llama31_floor_sum_predeclared.md).

## How to produce it
1. Open [`notebooks/reachscan_quickstart.ipynb`](../../notebooks/reachscan_quickstart.ipynb)
   in Colab (GPU runtime).
2. In the run-contract cell, set `TIER = "cross_family"`, pin `REVISION`, log
   in to Hugging Face, and confirm the model-specific token printed on the run
   card.
3. Run the format/yield sanity check, then the checkpointed full scan.
4. Download the run's artifacts into `artifacts/` here.
5. Derive the mod-8 family view from the *same* receipts (no model rerun):
   `python reproject_mod8.py artifacts/receipts.csv`.

## What lands here after the run
```text
artifacts/
  summary_by_depth.csv
  receipts.csv
  run_manifest.json
  summary_by_depth.csv.meta.json
  receipts.csv.meta.json
  runtime_provenance.json      # GPU, torch, transformers, python, model revision
figures/
  target_reachability.png      # R_T(f) with Wilson intervals
  answer_yield_audit.png       # ok_answers / attempts — the trust check
ARTIFACTS.sha256
REPRODUCTION_NOTE.md
```

## Honest scope
One model, one task, finite budget, one sampler — a *measurement*, not a law, and
not a generality claim. The shipped tool measures autoregressive models you have
token-level access to (open weights, or a frontier model if you hold its weights);
it does not run on hosted chat APIs. See the repo README for the full boundary.
