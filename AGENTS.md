# AGENTS.md — ReachScan

**ReachScan is a measurement instrument, not a model and not a claim.** It
estimates the *future field* of a committed reasoning prefix: given a model that
has partially committed to a line of reasoning, which answer-futures remain
reachable, and how target reachability changes as commitment deepens. It is a
black-box measurement over outputs.

This file is the shared baseline. It is read natively by Codex and Cursor
(verified), and by other AGENTS.md-aware tools per the cross-tool standard. The
full operator workflow is in
[docs/agents/reachscan-operator.md](docs/agents/reachscan-operator.md). Native
per-tool wrappers: `.claude/skills/` (Claude Code), `.agents/skills/` (Codex),
`.cursor/rules/` (Cursor).

## Honesty contract (never violate)

1. **A mock run is NOT a result.** `MockSource` is a deterministic fixture that
   proves the pipeline runs; its numbers are illustrative. Always say which
   source produced a number.
2. **A zero count is a finite-budget observation, not a proof of zero
   probability.** Every count is conditional on the declared sampler and on `M`.
3. **Every measurement is sampler-relative and projection-relative.**
4. **Two tasks in one model is not generality.** Cross-model/task claims are
   earned by replication, not asserted.
5. **No internal-state claims.** The field is over outputs only.

## Install
```bash
pip install -e .          # core (mock path, zero heavy deps)
pip install -e ".[hf]"    # add a real HuggingFace model source
pip install -e ".[test]"  # tests
```

## Run (mock vs real)
```bash
reachscan-demo --out /tmp/smoke --M 16                    # MOCK fixture — not a result
reachscan-demo --hf <MODEL_ID> --out <run_dir> --M 128    # real (needs [hf] + a runtime)
```
A GPU/accelerator is recommended for real runs; small models may run on CPU/Apple
Silicon. Most operation (projection design, interpreting `examples/demo_run/`,
auditing) needs **no model at all**.

The shipped real-model path runs a **local open-weights model** (via HuggingFace):
the source contract needs token-level prefix continuation, which closed/API-only
chat models do not expose. You **cannot** point the shipped tool at a closed API
model out of the box; a future adapter could wrap one with weaker guarantees.

## Artifacts & provenance
Runs write `summary_by_depth.csv`, `receipts.csv`, `run_manifest.json`, each with
a `.meta.json` provenance companion. Verify the shipped tree with
`sha256sum -c MANIFEST.sha256` (Linux) / `shasum -a 256 -c MANIFEST.sha256`
(macOS). Every reported number must trace to a named input in `run_manifest.json`.

## What not to do
- Don't present mock numbers as findings.
- Don't generalize from one task or one model.
- Don't claim anything about model internals.
- Don't report a number you can't trace to the run manifest.
