# Changelog

## 0.3.1 — 2026-06-24 (prediction evaluator; no engine schema bump)

Turns a pack's predeclared `prediction` block into a mechanical
`supported / failed / inconclusive` verdict computed from **raw receipts**. The
morphology claim becomes losable instead of a post-hoc reading. Layer over the
engine; `engine_schema` stays `0.3.0` (the evaluator reads existing receipts).

- **`reachscan.prediction`** — `evaluate_prediction(rows, prediction, classes,
  target_class)` with three test types over the WRONG-answer field:
  `family_structure` (normalized entropy vs `expected_mode` concentrated/diffuse/
  mixed), `morphology_mode` (capture/shatter/mixed), `family_before_atom`
  (two-grain, with an initial target-viability precondition). `any_test_failed` is
  the only accepted loss rule; unknown rules/test types → `inconclusive`. Thin
  data, missing bands, and already-collapsed targets are `inconclusive`, never a
  false support. `family_before_atom` judges masses over **parsed (ok) answers
  only** and needs `min_n_per_depth` ok answers per depth, so a deep depth that is
  all `no_answer` is `inconclusive` (yield/extraction failure is not a family
  collapse), never `supported`. Plus `evaluate_run(pack, result)`,
  `rows_from_result`, `prediction_hash`, `write_prediction_verdict`,
  `update_manifest_with_verdict`.
- **CLI** `reachscan prediction evaluate <run_dir> --projection <pack_dir>` —
  writes `prediction_verdict.json` and records a `prediction` block in
  `run_manifest.json`. Refuses a run whose `projection_pack_hash` differs from the
  pack (projection lock); `applies_to.source_arm` filters to one declared arm.
- **Tests** — the six packaged receipt fixtures (supported / failed / two
  inconclusive / source-arm-filtered / diffuse-mode) all reproduce their declared
  outcomes, plus unit checks for loss rules, test types, `expected_mode`,
  viability, and yield robustness. Tests 66 → 81.
- **Docs** — `docs/PREDICTION_CONTRACT.md`; pack README + `projection.yaml` updated
  (note: editing `projection.yaml` changes the behavior-bearing pack hash, as
  intended). Demo + `MANIFEST.sha256` regenerated.

## 0.3.0 — 2026-06-24 (projection packs + receipt/manifest binding; engine_schema 0.2.8 → 0.3.0)

Adds the **projection pack** system and its binding into receipts and the
manifest. (The prediction *evaluator* is not in this release; the predeclared
`prediction` block is carried and hashed, not yet executed — it arrives in 0.3.1.)

- **`reachscan.projection_pack`** — a projection pack is a directory
  (`projection.yaml` + `adapter.py` + `fixtures.jsonl` + README) that declares a
  task-specific answer lens:
  - `load_projection_pack()` builds a pack that **also satisfies the engine
    `Projection` protocol**, so `reach_scan` runs a pack with no engine changes.
  - `hash_projection_pack()` computes a **behavior-bearing** `projection_pack_hash`
    over `projection.yaml` + `adapter.py` + `fixtures.jsonl` (path + bytes) — a
    parser/classifier edit cannot keep the same hash (hashing the YAML alone would
    silently miss parser/classifier/fixture changes).
  - `validate_fixtures()` runs labeled fixtures through the adapter and flips
    `fixtures_validated` only on a clean pass; an undeclared emitted class fails loud.
- **Floor-sum pack** — `examples/projections/floor_sum_mod8/` (the flagship as a
  formal pack), with a self-contained adapter and a `run_pack_demo.py`. It encodes
  the deliberate gap between the **outcome check** (exact 532) and the **projection
  class** (residue fiber `residue_4`, which also contains 540, 916, …).
- **Engine binding (the unfreeze).** Receipts gain `projection_class`,
  `parsed_answer`, `target_hit` (the exact outcome check, distinct from `is_target`
  = target-class membership), `parse_status`, `projection_id/version/pack_hash`,
  `source_arm`, exposure fields (stubbed `not_checked` at this claim level), and
  `raw_completion`. The manifest gains a `projection_pack` block and `source_arm`.
  The engine stays generic: a plain projection has no `pack_meta`, so the block is
  absent and the run-constant columns are empty (**back-compatible**).
- **CLI** `reachscan projection validate|inspect <pack_dir>` (new `reachscan`
  console entry point); the existing `manifest["projection"]` name string is kept.
- **Deps:** YAML is gated behind a new optional `projection` extra (`pip install
  reachscan[projection]`); `import reachscan` stays dependency-free (lazy import).
- **Schema:** `engine_schema` `0.2.8 → 0.3.0` (receipts + manifest grew).
  `read_result` tolerates pre-0.3.0 artifacts (new columns default empty). Tests
  50 → 66 (`tests/test_projection_pack.py`). Demo + `MANIFEST.sha256` regenerated.

## 0.2.9 — 2026-06-24 (notebook checkpoint-stitch correctness; no schema bump)

- **The quickstart notebook now assembles checkpoints with `stitch_results()`**
  instead of copying the first checkpoint's manifest. v0.2.8 added a per-checkpoint
  `cost` block; because each per-depth checkpoint only covers its own depth, the
  old hand-rolled stitch (keep depth 0's manifest) **under-reported total generated
  tokens and wall-clock by roughly the depth count** in the final
  `run_manifest.json`. `stitch_results()` concatenates depths in order and sums the
  cost block, so a checkpointed (e.g. disconnect-resumed) Colab run now reports the
  same total cost as a single pass. Per-rollout receipts were always correct; only
  the rolled-up cost summary was affected.
- **Regression test** (`test_notebook_style_stitch_reports_full_run_cost`) asserts
  the old single-manifest approach under-reports and that the notebook's exact
  `stitch_results([...])` expression matches a single-pass run on both total tokens
  and seeds. Tests 49 → 50.
- No engine/measurement change: `engine_schema` stays `0.2.8`; floor-sum R_T values
  unchanged. Package/provenance version bumped 0.2.8 → 0.2.9; demo + `MANIFEST.sha256`
  regenerated.

## 0.2.8 — 2026-06-24 (cost instrumentation; first schema bump since 0.2.4)

**What a scan now reports about its own cost.** The engine measures; callers
present. Cost is split into two tiers that are never conflated: **work**
(generated tokens) is deterministic given seed+model and is reproducible;
**environment** (wall-clock, hardware) is noisy provenance, not a measurement.

- **Receipts gain `n_new_tokens`** — the generated-token count per rollout (the
  engine already had `len(new_ids)` in hand for the cap-hit check and now keeps
  it). Deterministic, so it is the reproducible measure of work done.
- **The run manifest gains a `cost` block** with `work` (`gen_tokens_total`,
  `gen_tokens_by_depth`) and `environment` (`wall_clock_s_total`/`_by_depth`,
  `runtime`, `started_utc`, `ended_utc`). The block grows during the run, so a
  partial result handed to `on_depth_complete` already carries cost-so-far.
- **The engine stays substrate-agnostic** — it never imports torch. Hardware
  identity comes *from the source*: `HuggingFaceSource.describe_runtime()` reports
  device/GPU/dtype/library versions; the engine records whatever it returns (and a
  source without the method, like the mock, contributes `runtime: null`). A source
  that raises cannot abort a scan.
- **`reachscan.estimate_cost(plan, …)`** — an a-priori cost helper. The rollout
  *count* is exact; the *seconds* are an explicitly-labeled **upper bound**
  (assumes every rollout fills `max_new_tokens` at the trace-generation token
  rate, ignoring deeper-prefix prefill). Honest by construction: it is a ceiling
  to refine live, not a confident point estimate.
- **`reachscan.stitch_results(parts)`** — combines per-depth checkpoints into one
  whole-run result and **sums the cost block across them**. Each checkpoint's
  manifest only covers its own depth; naively keeping one would under-report total
  tokens/wall-clock by the number of depths. Verified: stitched gen-token total
  equals a single-pass run, and seeds remain identical.
- **`on_progress` callback** on `reach_scan` — fires once per rollout with
  `{depth_index, rollout_index, rollouts_in_depth, depths_total}` for an
  intra-depth progress bar. Default `None` keeps the library silent.

**Schema.** `engine_schema` bumped `0.2.4 → 0.2.8` — the first measurement-schema
change since 0.2.4, because receipts gained a column and the manifest gained the
cost block. **Backward-compatible:** `read_result` tolerates pre-0.2.8 artifacts
that lack the `n_new_tokens` column (the count defaults to `0`); the floor-sum R_T
values in the regenerated demo are unchanged. Tests 43 → 49. `MANIFEST.sha256`
regenerated.

## 0.2.7 — 2026-06-23 (run-contract gate; no schema bump)

**Run control / notebook safety**
- Added `reachscan.run_contract`, a lightweight notebook helper that forces an
  explicit run tier before any HuggingFace model loads. The quickstart now starts
  from `TIER = None` and hard-stops until the user selects `smoke`,
  `paper_family`, `cross_family`, or `custom`.
- The run card prints the model id, revision, gated-model status, task,
  projection, sampler, depth plan, artifact directory, claim ceiling, and a
  model-specific confirmation token. This prevents the smoke model
  (`Qwen/Qwen2.5-1.5B-Instruct`) from silently becoming the intended Llama run
  (`meta-llama/Llama-3.1-8B-Instruct`).
- Real tiers require a Hugging Face revision pin unless `ALLOW_UNPINNED=True` is
  set deliberately. The floor-sum prompt now stays centralized in the contract
  helper and preserves the `\boxed{}` answer-format instruction needed for the
  extractor/yield check.
- Added `docs/CHOOSE_YOUR_RUN.md` as the repo front door for choosing a tier,
  rigor preset, and claim ceiling. Updated the open-weights floor-sum example
  and Llama predeclaration to point at the contract cell instead of manually
  editing `MODEL_ID`.

**Versioning**
- Package/provenance version bumped 0.2.6 → 0.2.7. `engine_schema` remains
  `0.2.4` because the CSV/manifest measurement schema and engine math are
  unchanged.

## 0.2.6 — 2026-06-23 (checkpointed Colab runs; diagnostics; no schema bump)

**Run control / Colab survivability**
- `reach_scan` now supports `run_depth_indices`, a seed-preserving way to run a
  subset of the effective depth plan. This is for checkpoint/resume workflows:
  a resumed depth keeps its original `depth_index`, so the binding seed rule
  (`sha256(base_seed|depth_index|rollout_index)`) remains unchanged. Default
  behavior still runs every depth.
- `reach_scan` now accepts `on_depth_complete`, an optional callback invoked
  after each completed depth with the current partial result. The notebook uses
  this to write artifacts as progress is made instead of waiting for the entire
  scan to finish.
- `metadata.read_result(outdir)` reads artifacts written by `write_result()` back
  into a `ReachScanResult`, allowing completed per-depth checkpoints to be loaded
  and stitched into the final output without rerunning those depths.
- The quickstart notebook now has a resource/plan diagnostics cell and a
  checkpointed Section 5. It caches the generated reference trace, writes one
  checkpoint directory per completed depth, skips completed depths on rerun, and
  assembles final `summary_by_depth.csv`, `receipts.csv`, and `run_manifest.json`
  from the checkpoint set.

**Versioning**
- Package/provenance version bumped 0.2.5 → 0.2.6. `engine_schema` remains
  `0.2.4` because the ordinary CSV/manifest output schema is unchanged.
- Batched generation remains deferred: batching can improve GPU utilization, but
  it changes generation/seed semantics and needs a deliberate v0.3 contract, not
  a silent notebook patch.

## 0.2.5 — 2026-06-23 (real-model adapter fix; verified on GPU)

**Reference adapter (the bug that blocked live runs)**
- **`HuggingFaceSource.encode_prompt` now returns integer token ids, not the
  strings `['input_ids', 'attention_mask']`.** The previous body called
  `apply_chat_template(..., tokenize=True)` and then `list(...)` on the result.
  On current `transformers`, that call returns a dict-like `BatchEncoding`, so
  `list()` yielded its *keys* (strings) instead of token ids; downstream,
  `sample_completion` did `torch.tensor([list(input_ids)])` and raised
  `ValueError: too many dimensions 'str'`. This blocked the *entire* real-model
  path — every scan that uses `GeneratedPrefixSource` calls `encode_prompt` — not
  just a sanity cell. The fix applies the chat template as **text**
  (`tokenize=False`) and then tokenizes that text in a separate call, indexing
  `["input_ids"]`, which is robust to both the `BatchEncoding` and plain-list
  return shapes. The no-template fallback is preserved (and now correctly avoids
  double-adding special tokens). Root cause confirmed empirically on an A100
  (returned a 71-element all-integer id list; first token `151644` = Qwen's
  `<|im_start|>`), not inferred from the traceback alone.
- **Regression coverage so this class of bug fails in CI, not on a GPU.** Added
  mocked-tokenizer tests for `encode_prompt` (chat-template path asserts integer
  ids rather than `BatchEncoding` keys; no-template fallback path) and a runtime
  type guard in `sample_completion`: non-integer `input_ids` now raise a clear
  `TypeError` *before* `torch.tensor`, instead of the opaque "too many dimensions
  'str'" deeper down. Test count 31 → 34; the notebook smoke run is now a backstop,
  not the first detection point.

**Versioning / docs**
- `package_version` bumped 0.2.4 → 0.2.5 across `pyproject.toml`,
  `reachscan.__init__`, `metadata.py` (framework stamp), `CITATION.cff`, the
  README status line, and `docs/PRODUCT_ARCHITECTURE.md`. `engine_schema` stays
  `0.2.4`: the manifest/CSV schema is unchanged — this release touches only the
  live adapter and provenance stamp.
- **Zenodo DOI wired in (carried over from the v0.2.4 tag, ships in this
  release).** README badge and `CITATION.cff` use the **concept** DOI
  `10.5281/zenodo.20808922` (always resolves to the latest version);
  `docs/PRODUCT_ARCHITECTURE.md` records the per-version DOIs (v0.2.4 =
  `10.5281/zenodo.20808923`; v0.2.5 PENDING until deposit). Author ORCID
  (`0009-0006-3649-4438`) is in `CITATION.cff` and `.zenodo.json`.
- **Notebook prose cleanup ships here.** The quickstart notebook's conversational
  notebook prose was stripped on `main` after the v0.2.4
  tag was cut; the frozen v0.2.4 deposit still carries the old prose. The v0.2.5
  deposit self-corrects it rather than re-cutting v0.2.4.
- `examples/demo_run/` regenerated under v0.2.5 (framework stamp only; R_T values
  and schema unchanged). `MANIFEST.sha256` regenerated.

## 0.2.4 — 2026-06-22 (hardening release; addresses an independent code review)

**Code / measurement integrity**
- **Undefined reachability is no longer reported as zero.** When `ok_answers == 0`
  (total extractor failure), `target_reachability` and its Wilson interval are now
  `NaN` and a new `rate_defined=False` flag is set — previously R_T was `0.0` with
  interval `[0,0]`, so a failed extraction looked like *certain* zero reachability.
  `source_separation` now raises on undefined rows instead of contrasting them.
- **`[hf]` extra now includes `accelerate`** (required by `device_map="auto"`); a
  clean `pip install ".[hf]"` could previously fail to load a model.
- **Projection constructors validate their domain:** `ModuloProjection` and
  `TargetFiber` reject modulus ≤ 0 and normalize `target_residue` mod the modulus
  (no more divide-by-zero or silently-unreachable targets).
- **Summary CSV gains `rate_defined` and a `field` column** serialized as a JSON
  array of `[bucket, count]` pairs (robust to non-scalar bucket keys such as
  tuples — a plain object dump would crash for a valid custom projection;
  previously documented but not written). `engine_schema` bumped to `0.2.4`. A
  mocked-`transformers` test now exercises the HuggingFace adapter's
  generation-config construction without downloading weights.
- README formal object now conditions `R_T` on a valid extraction and defines
  answer yield explicitly — and clarifies that cap-hits are flagged
  *independently* (a capped generation that still parses is counted, not excluded).

**Also in this release (docs / infrastructure since 0.2.3)**
- **Honesty contract gains an evidence-hierarchy rule:** raw artifacts
  (`receipts.csv` / `summary_by_depth.csv` / `run_manifest.json`) are
  authoritative; generated prose (ledgers, READMEs, plot captions, notebook
  markdown, agent summaries) is provisional. Every interpretive claim must be
  recomputed from the raw rows — never summarize a summary. Added to `AGENTS.md`,
  the operator guide (with a "verify before you conclude" checklist), all three
  per-tool adapters, and the ledger/reproduction-note templates. This guards
  against generated narrative becoming accidental authority.
- **Cross-model experiment scaffold (pre-run):** `docs/experiments/`
  (predeclared Llama-3.1-8B floor-sum recipe + run ledger) and
  `examples/openweights_floor_sum/` (README + `reproject_mod8.py`); the quickstart
  notebook generalized to any open-weights autoregressive model.
- **Agent-onboarding layer added.** A dialect-neutral operator guide
  (`docs/agents/reachscan-operator.md`) plus thin per-tool adapters: `AGENTS.md`
  (shared baseline, read by Codex/Cursor and other AGENTS.md-aware tools),
  `.claude/skills/reachscan-review/` (Claude Code), `.agents/skills/reachscan-review/`
  (Codex), `.cursor/rules/reachscan-review.mdc` (Cursor). Shared templates and
  reference live once under `docs/agents/`. The honesty contract (mock ≠ result,
  finite-budget, sampler/projection-relative, no internal-state claims,
  one-task ≠ generality) travels in every adapter. `mcp/README.md` is a
  placeholder for a future callable-tool layer.
- **README:** noted that the shipped real-model source is a local open-weights
  (HuggingFace) model — closed/API chat models are not supported out of the box.
- `MANIFEST.sha256` regenerated; shipped `examples/demo_run/` regenerated under
  v0.2.4 (adds the `rate_defined`/`field` columns; R_T values unchanged).

## 0.2.3 — 2026-06-22 (coherence-review hardening; all changes backward-compatible)

A second independent cross-review of the v0.2.2 package found small public-facing
coherence gaps and a real contract-leakage point. Every change below is additive
to the contract surface; nothing a v0.2.2 caller did breaks.

**Contract / measurement integrity**
- The binding `Projection` consistency rule (if two answers share a `project()`
  bucket they MUST share the same `is_target()`) is now ENFORCED by the engine in
  a single pass. A custom projection that violates it raises `ValueError` (loud and
  local) instead of silently producing incoherent target reachability.
- `SamplerPolicy` validates on construction (`__post_init__`): `temperature >= 0`,
  `top_p in (0, 1]`, `top_k None or >= 1`, `repetition_penalty > 0`,
  `max_new_tokens >= 1`. Malformed decode policies fail before reaching a model.
- `source_separation` now enforces what it documents: both scans must share the
  same ORDERED depth plan (fraction AND resolved `committed_len`), not merely the
  same rounded fractions.

**Named-inputs completeness**
- Run manifest plan rows gain `resolved_committed_len` (the actual committed-token
  count used at each depth), alongside the raw `committed_len` override field.
- Run manifest records `package_version` (the release) distinct from
  `engine_schema` (the manifest schema). `engine_schema` is bumped to `0.2.3`
  because the plan rows changed.

**Terminology (floor-sum vocabulary removed from the general surface)**
- `DepthSummary` gains `ok_answers` (= `status == "ok"` count). `numeric` is kept
  as a legacy alias. The summary CSV writes both columns; the CLI header reads `ok`.
- `SeparationRow` gains `ok_correct` / `ok_wrong` aliases for
  `numeric_correct` / `numeric_wrong`.

**Reference adapter**
- `HuggingFaceSource` no longer drops a valid `pad_token_id` of `0` (the truthiness
  fallback wrongly replaced `0` with EOS).

**Artifacts / metadata**
- Shipped `examples/demo_run/` regenerated with the v0.2.3 code (the v0.2.2
  artifacts were still stamped `v0.2.1`).
- `.zenodo.json` relation to the SAT predecessor changed from `isSupplementedBy`
  to `references` (the SAT record is prior related work, not a supplement to this).
- README scope wording softened (the non-included research tooling is described by
  where it lives, not as "held privately").

## 0.2.2 — 2026-06-11 (pre-push fixes from an independent cross-review)

- **Test self-runner moved to the end of the file.** It previously sat
  mid-file — a v0.2.0 layout that the 0.2.1 additions repeated — so
  `python tests/test_engine.py` collected only the 12 tests defined above it,
  reported "12/12 passed", and exited success before the remaining 9 (including
  all seven 0.2.1 additions) were even defined. pytest/CI collect by name and
  were never affected. The runner now sits at EOF with a keep-at-end guard
  comment and prints the collected count, so under-collection is visible if the
  layout ever regresses. Both run paths now report 21/21.
- **Shipped `examples/demo_run/` regenerated at the demo default** (M=128,
  seed 0): a first user's quickstart output now matches the shipped artifacts,
  which were previously generated at M=64.

Both issues were reported by an independent cross-model review of the 0.2.1
package and reproduced here before fixing.


## 0.2.1 — 2026-06-11 (pre-DOI hardening; all changes contract-additive)

Audit-driven release. Every change below is additive to the contract surface;
nothing that a v0.2.0 caller did breaks.

**Contract / measurement integrity**
- `SamplerPolicy` gains `top_k` (None = disabled, never "model default") and
  `repetition_penalty`; the engine passes the FULL declared policy across the
  plug. `sample_completion` adds these kwargs plus a binding forward-compat
  clause: sources MUST accept unknown keyword sampler parameters
  (`**sampler_extras`), and SHOULD raise on non-default values they cannot
  honor. The paper's decoding policy (top_k=10) is now expressible.
- `HuggingFaceSource` builds an EXPLICIT `GenerationConfig` from the declared
  policy alone — the model's own `generation_config` defaults are no longer
  silently merged (previously an undeclared `top_k=50` could ride along). The
  adapter declares `sampler_semantics`, recorded in every run manifest. An
  attention mask is now passed explicitly.
- Engine flags `hit_token_cap` on every receipt and counts `cap_hits` per
  depth: the budget audit that exists without finish reasons. Source-flagged
  `truncated` remains reserved for finish-reason-capable sources (optional
  capability planned for v0.3; the required surface will not change).
- Seed-range rule made explicit and binding: seeds are integers in
  `[0, 2**64)`; sources must accept the full range.

**Named-inputs completeness**
- Run manifest now records: `stop_token_ids`, `include_prompt_only`, the
  prefix source's `provenance` (trace seed + trace sampler for generated
  traces), `sampler_semantics`, the effective plan including `committed_len`,
  and an `engine_schema` version.

**Engine semantics**
- `include_prompt_only: bool = True` makes the prepended f=0 row an explicit,
  recorded decision; `depth_index` semantics documented (indexes the effective
  plan).
- `DepthSpec.committed_len` (optional) specifies a depth by committed-token
  COUNT, implementing contract v3 R5's near-terminal-anchor option (e.g. the
  paper's 99.9% row as `L-1`) that the dataclass previously could not express.
- Fail-loud validation: fractions outside [0, 1], rollouts < 1, out-of-range
  `committed_len`, and empty traces/plans now raise instead of measuring
  silently.

**Reference components**
- `ExactMatch` accepts non-integer ground truths ('5/8', 'x+1') via shared
  canonicalization (int-like values normalize; previously it crashed with a
  raw `ValueError`). The binding bucket/target consistency rule is preserved.
- `MockSource` v2: drift is trace-relative (the prompt no longer pre-saturates
  it), emissions respect `max_new_tokens` (cap accounting is exercisable
  GPU-free), and budget-sized filler gives generated traces real depth — the
  default demo now SHOWS the collapse curve (R_T 0.64 -> 0.05 with basin mass
  rising to ~0.95) instead of a flat table.

**Process**
- `ruff.toml` (critical-rules gate) + a CI lint step; tests grown 14 -> 21.
- Versioning note, for the record: two differing v0.2.0 trees circulated
  (PUBLIC and PUBLIC_2) under one version string. From 0.2.1 forward: any byte
  change bumps the version, gets a CHANGELOG entry, and a git tag.

## 0.2.0 — 2026-06

- `contrast.py`: source-conditioned separation with Newcombe difference CIs;
  `examples/source_contrast.py`. Second iteration (the "PUBLIC_2" tree) added
  HF `revision` pinning, attempts-vs-numeric denominators in contrast rows,
  and moved the paper's Wilson numbers out of the tests.

## 0.1.0 — 2026-06

- Initial instrument: three contracts + engine, reference projections, mock
  and HF sources, provenance-stamped artifacts, demo CLI, 12 tests, CI,
  Apache-2.0 surface.
