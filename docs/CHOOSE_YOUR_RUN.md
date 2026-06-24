# Choose your ReachScan run

ReachScan runs should start with an explicit contract, not an edited model
string. The quickstart notebook uses `reachscan.run_contract` to make the user
choose a tier before any model loads.

## The rule

Do not treat a smoke model as the experiment. The notebook has no active default
`MODEL_ID`; leaving `TIER = None` stops the run.

Every confirmed run prints:

- model id and revision;
- task and projection;
- sampler and depth plan;
- artifact directory;
- claim ceiling;
- model-specific confirmation token.

## Tiers

| Tier | Model | Default rigor | Use it for | Claim ceiling |
|---|---|---:|---|---|
| `smoke` | `Qwen/Qwen2.5-1.5B-Instruct` | `smoke_budget` | Verify Hugging Face loading, generation, extraction, and artifact shape. | No scientific claim. |
| `paper_family` | `Qwen/Qwen2.5-Math-7B-Instruct` | `research` | A Qwen-family run close to the flagship paper model. | Single-model, same-family measurement. Not cross-architecture. |
| `cross_family` | `meta-llama/Llama-3.1-8B-Instruct` | `research` | First Llama cross-family floor-sum check. | One cross-family data point, not a generality law. |
| `custom` | User-supplied HF id or local path | `standard` | Your own open-weights autoregressive model. | Must be written explicitly before interpretation. |

## Rigor presets

| Rigor | Depth plan | Checkpointed | Use it for |
|---|---:|---:|---|
| `smoke_budget` | `0.0x16, 0.5x16, 1.0x16` | yes | Cheap path verification. |
| `standard` | `0.0x128, 0.25x64, 0.5x64, 0.75x128, 0.9x128, 1.0x128` | yes | Normal declared run. |
| `research` | Same as `standard` | yes | Revision-pinned run intended for artifacts and interpretation. |

## Revision discipline

For `paper_family`, `cross_family`, and `custom`, set `REVISION` to a Hugging
Face model commit SHA before interpreting the result. The notebook will refuse
to run those tiers unpinned unless `ALLOW_UNPINNED = True` is set deliberately.
If an unpinned run is allowed, record that fact in `docs/experiments/run_ledger.md`.

## Llama designs

The default `cross_family` tier is a native Llama trace: Llama generates its own
reference trace on the same floor-sum task, then ReachScan slices that trace.
That is the clean first cross-family measurement.

A fixed-prefix Llama probe is different: Llama is handed Qwen's committed prefix
text and asked to continue from it. That is an off-policy portability probe and
should be declared separately.

## After a run

Before interpreting results, check the raw artifacts in this order:

1. `run_manifest.json`: model, revision, sampler, plan, seed rule.
2. `summary_by_depth.csv`: `ok_answers`, `cap_hits`, `R_T`, Wilson interval,
   dominant bucket, entropy.
3. `receipts.csv`: raw per-rollout extraction statuses and values.
4. `runtime_provenance.json`: GPU, package/runtime versions, model placement.

Generated prose, notebook summaries, and plot captions are provisional. Recompute
claims from the raw rows.

## Maintainer verification checklist

Before merging a run-control change:

1. Run `python -m pytest -q`.
2. Run `python -m ruff check .`.
3. Run `git diff --check`.
4. Verify the quickstart has no active hard-coded experiment model:
   - no active `MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"`;
   - no active `MODEL_ID = "meta-llama/Llama-3.1-8B-Instruct"`;
   - `build_run_contract(...)` appears in the notebook.
5. Verify no AI-authorship or conversational-scaffold leakage in live surfaces:
   - no AI-authorship trailers;
   - no assistant session metadata;
   - no assistant-provider noreply addresses;
   - no conversational notebook prompt that tells the user what they "are about
     to be."
6. Regenerate `examples/demo_run/` and `MANIFEST.sha256` when the package version
   changes.
7. Confirm `engine_schema` is unchanged unless the CSV or manifest measurement
   schema actually changed.
