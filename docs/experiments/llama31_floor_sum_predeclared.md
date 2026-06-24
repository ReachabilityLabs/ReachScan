# Predeclared experiment — Llama-3.1-8B-Instruct on floor-sum

**Status:** PREDECLARED (pre-run). No model outputs yet.
**Date:** 2026-06-22

This locks the experiment design *before* running, so the result cannot be
cherry-picked after the fact (mirrors the paper's preregistration discipline).
Fill in the artifacts and the run-ledger row only after the real run.

## What this tests (and what it does NOT)
First **cross-model** reach-scan: does the future-field morphology appear on a
model the instrument was **not** built around? It is **not** a reproduction of the
paper — it is "same task, different model." Every outcome is informative (similar
collapse / shifted / diffuse / robust / different wrong basin).

## Locked configuration
- **Model:** `meta-llama/Llama-3.1-8B-Instruct` (gated; license accepted).
- **Revision:** pin the exact commit SHA at run time; record it in
  `run_manifest.json` and the run ledger.
- **Smoke model (pipeline check):** `Qwen/Qwen2.5-1.5B-Instruct` (ungated).
- **Task:** floor-sum — "Compute the sum of floor((3n+7)/5) for n = 1..40";
  correct answer **532**.
- **Primary projection (the claim-bearing lens):** the `floor_sum_mod8` projection
  pack (built-in), target class `residue_4`. The purpose of this run is
  **morphology**, so target reachability `R_T(f)` is mass on the residue-4 *fiber*;
  the exact answer 532 is recorded per-receipt as `target_hit`. The pack is
  fixture-validated and its `projection_pack_hash` is recorded in the manifest.
- **Companion / sanity lens (same receipts, post-hoc):** the `floor_sum_exact`
  pack (built-in), target class `target` = exactly 532. This reports exact-answer
  reachability as a cross-check; it is **not** the main claim-bearing lens.
- **Prefix source:** `GeneratedPrefixSource` (Llama's *own* generated trace),
  trace seed 0, trace `max_new_tokens=2048`. NB: this is "same task, each model on
  its own native trace" — **not** "same committed prefix."
- **Rollout sampler:** temperature 0.7, top_p 1.0, top_k None,
  repetition_penalty 1.0, `max_new_tokens=512`. `base_seed=0`.
- **Depth plan (fraction × M):** 0.00×128, 0.25×64, 0.50×64, 0.75×128,
  0.90×128, 1.00×128.
- **Run path:** `notebooks/reachscan_quickstart.ipynb`, with
  `TIER = "cross_family"` and `PROJECTION_PACK = "floor_sum_mod8"` in the
  run-contract cell. The run card must show the pack id, `projection_pack_hash`,
  `target class: residue_4`, and `fixtures: PASS` before you confirm.
  Do **not** manually edit a hidden `MODEL_ID`; the notebook should fail until
  the tier, revision, pack fixtures, and confirmation token all agree.

## Predeclared reading rules
1. **Check answer yield first.** If `ok_answers` at the prompt-only state is low
   relative to attempts, the extractor isn't catching Llama's format — fix the
   prompt/extractor and rerun before interpreting any R_T. Low yield ≠ low
   reachability.
2. **Foreclosure signal** = a *sustained* fall in `R_T(f)` across depth before
   answer exposure (not a single dip).
3. **Exposure caveat:** late depths (esp. f=1.0) may already contain the answer in
   the committed trace; treat those as post-hoc morphology.
4. Report `R_T` with Wilson intervals; describe the **trend**, not one number.

## Honesty caveats (binding)
Finite-budget (declared M), sampler-relative, projection-relative estimate of a
black-box behavioral object. One model, one task — **not** a generality claim.
Seeds reproduce sampling decisions given identical logits, not bitwise across
hardware; promise the **shape** + recorded provenance.

## Recorded after the run
`summary_by_depth.csv`, `receipts.csv`, `run_manifest.json`, the `.meta.json`
companions, `runtime_provenance.json` (GPU / torch / transformers / python /
model revision), `ARTIFACTS.sha256`, `REPRODUCTION_NOTE.md`, and a row in
`docs/experiments/run_ledger.md`.
