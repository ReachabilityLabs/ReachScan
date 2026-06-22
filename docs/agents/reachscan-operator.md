# ReachScan operator guide (canonical)

> **This file is the single source of truth.** The per-dialect wrappers
> (`AGENTS.md`, `.claude/skills/…`, `.agents/skills/…`, `.cursor/rules/…`) are
> thin adapters that inline the honesty contract and point here. Edit the
> operator workflow **here**; keep the wrappers' inlined honesty contract in sync.

ReachScan is the **operating harness above the `reachscan` engine**. The engine
measures; an agent using this guide helps design, run, audit, and interpret the
measurement *without misusing it*. ReachScan estimates, for a committed reasoning
prefix, the distribution of answer-futures a source can still reach (the **future
field**), and how target reachability changes as commitment deepens. It is a
black-box behavioral measurement, **not** a probe of model internals.

## Rule 0 — the honesty contract (never violate)

- **A mock run is NOT a result.** `MockSource` is a deterministic fixture that
  proves the pipeline runs. Its numbers are illustrative only. Never present mock
  output as a finding. Always state which source produced a number.
- **A zero count is a finite-budget observation, not a proof of zero
  probability.** Every count is conditional on the declared sampler and on `M`
  (rollouts per depth).
- **Every measurement is sampler-relative and projection-relative.** Change the
  sampler or the projection and you are measuring a different conditional object.
- **Two tasks in one model is not generality.** Cross-model / cross-task claims
  are earned by replication, not asserted.
- **No internal-state claims.** The field is over outputs; it says nothing about
  activations or hidden state.

If a request would require breaking one of these (e.g. "prove the model can never
recover"), surface the limit plainly instead of complying.

## Workflow

### 0. Preflight (once per session)
Confirm you're at the `reachscan` repo root: `pyproject.toml`, `src/reachscan/`,
and `tests/test_engine.py` should all exist. If `reachscan-demo` is not found,
either `pip install -e .` from the repo root, or invoke without installing:
`PYTHONPATH=src python -m reachscan.tools.run_demo ...`.

### 1. Establish scope before measuring
Real model or mock? If real, is the `[hf]` extra installed with a working model
runtime (a GPU/accelerator is recommended; small models may run on CPU or Apple
Silicon)? **Much of this skill needs no model at all** — designing/validating
projections, interpreting the shipped `examples/demo_run/`, and provenance
auditing all run GPU-free; only a *real measurement* needs a model. If only the
mock is available, you may demonstrate the *pipeline*, but label every number as
fixture output, not a measurement.

**Substrate (important):** the shipped real-model path measures an
**autoregressive, token-emitting model you have token-level access to** — a local
open-weights model (typical HuggingFace path), your own model, or a frontier model
*if you hold its weights*. The line is **token-level access, not the
public/closed distinction**: it needs to freeze a committed prefix on token IDs
and sample continuations under a declared sampler, which a hosted chat **API**
does not expose — so the shipped tool can't run on an API model out of the box.
The contract is substrate-general (non-autoregressive/diffusion or agent
substrates could implement the same shape), but those are **research extensions,
not shipped**.

### 2. Define the task → design or validate a Projection
A `Projection` is the task-specific plug: `extract(text) -> ExtractedAnswer`,
`project(answer) -> bucket`, `is_target(answer) -> bool`. Ground truth/target
lives in the constructor, never as a hidden engine input.
- Shipped: `ExactMatch`, `ModuloProjection`, `TargetFiber` (floor-sum flagship =
  `ModuloProjection(8, target_residue=4)`). For other tasks, start from
  [`templates/projection_template.py`](templates/projection_template.py).
- **Enforce the binding consistency rule before running:** if two answers share a
  `project()` bucket they MUST share the same `is_target()` value. The engine
  raises `ValueError` on violation — catch it earlier by reading the projection.
- Sanity-check `extract` against the documented limitations (boxed-first, comma
  stripping, answer-cue fallback). Watch the `ok_answers` yield column.

### 3. Run — mock smoke first, then real
```bash
reachscan-demo --out /tmp/smoke --M 16                    # mock fixture (labeled)
reachscan-demo --hf <MODEL_ID> --out <run_dir> --M 128    # real (needs [hf] + runtime)
```
If `reachscan-demo` isn't on PATH:
`PYTHONPATH=src python -m reachscan.tools.run_demo --out <run_dir> ...`.
Programmatic entry: `reachscan.engine.reach_scan(...)`. `SamplerPolicy` validates
its fields on construction.

### 4. Read the output
Artifacts: `summary_by_depth.csv`, `receipts.csv`, `run_manifest.json`, each with
a `.meta.json` provenance companion. Full field-by-field readout (and the traps —
the `ok_answers` denominator, `cap_hits`, Wilson intervals, foreclosure-as-trend)
is in [`reference/interpreting_output.md`](reference/interpreting_output.md). Report the depth **trend**, not a single
number, and always quote R_T with its Wilson interval.

### 5. Audit provenance
- Integrity: `sha256sum -c MANIFEST.sha256` (Linux) or
  `shasum -a 256 -c MANIFEST.sha256` (macOS).
- Named inputs: open `run_manifest.json` — confirm `source`, `sampler_semantics`,
  the full `rollout_sampler`, `base_seed`, `seed_rule`, `include_prompt_only`,
  `package_version`, `engine_schema`, and `plan` with `resolved_committed_len`.
  If a number can't be traced to these, do not report it.
- Release assets (if relevant): `python scripts/verify_release_assets.py <dir>`.

### 6. Write an honest reproduction note
Use [`templates/reproduction_note.md`](templates/reproduction_note.md). It forces the named inputs, the result with
intervals, and the contract caveats, so the write-up cannot overclaim.

## Failure modes to catch
Mock-as-result · projection consistency violation · low `ok_answers` yield read as
low reachability · ignored `cap_hits` · `source_separation` on mismatched depth
plans · single-depth reading instead of the trend · cross-model/task
generalization from one run.

## Shared assets
The reusable templates and reference live in a **dialect-neutral** location next
to this guide, and every wrapper (Claude / Codex / Cursor) points here:
- [`templates/projection_template.py`](templates/projection_template.py)
- [`templates/reproduction_note.md`](templates/reproduction_note.md)
- [`reference/interpreting_output.md`](reference/interpreting_output.md)
