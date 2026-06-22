---
name: reachscan-review
description: >-
  Operate and audit a ReachScan reach-scan responsibly: design and validate
  answer projections, run mock and real-model scans, read the future-field
  readout, verify artifact provenance, and write an honest reproduction note.
  Use when measuring target reachability or foreclosure of a committed reasoning
  prefix, building or checking a Projection, interpreting summary_by_depth.csv /
  run_manifest.json, auditing a run, or writing up a reach-scan without
  overclaiming.
---

# ReachScan review (Codex)

Codex discovers this skill under `.agents/skills/`. It is a **thin adapter** over
the canonical operator guide — read it for the full workflow:
[docs/agents/reachscan-operator.md](../../../docs/agents/reachscan-operator.md).

## Honesty contract (never violate)
1. A mock run is **not** a result (`MockSource` is a fixture; say which source
   produced any number).
2. A zero count is a finite-budget observation, not proof of zero probability.
3. Every measurement is sampler-relative and projection-relative.
4. Two tasks in one model is **not** generality.
5. No claims about model internals — the field is over outputs only.
6. Raw artifacts (`receipts.csv` / `summary_by_depth.csv` / `run_manifest.json`)
   are authoritative; generated prose is provisional — recompute claims from the
   raw rows before writing them, never summarize a summary.

## Operate
1. **Preflight:** confirm repo root (`pyproject.toml`, `src/reachscan/`); if
   `reachscan-demo` is missing, `pip install -e .` or
   `PYTHONPATH=src python -m reachscan.tools.run_demo ...`.
2. **Projection:** start from
   `../../../docs/agents/templates/projection_template.py`;
   enforce the bucket/target consistency rule before running.
3. **Run:** mock smoke (`--M 16`) first, then real (`--hf <MODEL_ID>`, needs
   `[hf]` + a runtime).
4. **Read & audit:** report the depth *trend* with Wilson intervals; verify
   `MANIFEST.sha256` and trace every number to `run_manifest.json`.
5. **Write up:** use the reproduction-note template; never overclaim.

For full detail, traps, and field-by-field readout, follow the canonical guide
above. (Optional: add `agents/openai.yaml` here for Codex packaging metadata.)
