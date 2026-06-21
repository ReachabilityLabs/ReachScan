# Changelog

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
