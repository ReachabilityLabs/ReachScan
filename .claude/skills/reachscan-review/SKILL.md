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

# ReachScan review (Claude Code)

Claude Code discovers this skill under `.claude/skills/`. It is a **thin adapter**
over the canonical operator guide — read it for the full workflow, traps, and
field-by-field readout:
[docs/agents/reachscan-operator.md](../../../docs/agents/reachscan-operator.md).

## Honesty contract (never violate)
1. A mock run is **not** a result (`MockSource` is a fixture; name the source of
   any number).
2. A zero count is a finite-budget observation, not proof of zero probability.
3. Every measurement is sampler-relative and projection-relative.
4. Two tasks in one model is **not** generality.
5. No claims about model internals — the field is over outputs only.

## Operate
1. **Preflight:** confirm repo root (`pyproject.toml`, `src/reachscan/`); if
   `reachscan-demo` is missing, `pip install -e .` or
   `PYTHONPATH=src python -m reachscan.tools.run_demo ...`.
2. **Projection:** start from
   [docs/agents/templates/projection_template.py](../../../docs/agents/templates/projection_template.py);
   enforce the bucket/target consistency rule before running.
3. **Run:** mock smoke (`--M 16`) first, then real (`--hf <MODEL_ID>`, needs the
   `[hf]` extra + a local open-weights runtime).
4. **Read & audit:** report the depth *trend* with Wilson intervals (see
   [docs/agents/reference/interpreting_output.md](../../../docs/agents/reference/interpreting_output.md));
   verify `MANIFEST.sha256` and trace every number to `run_manifest.json`.
5. **Write up:** use
   [docs/agents/templates/reproduction_note.md](../../../docs/agents/templates/reproduction_note.md);
   never overclaim or imply generality.

Full detail: follow the canonical guide above.
