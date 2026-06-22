# Changelog

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
