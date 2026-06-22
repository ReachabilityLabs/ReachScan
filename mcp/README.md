# MCP server — PLANNED (not built)

This is a **placeholder** for the cross-agent tool layer, deferred by design (the
last rung). The instruction layer above — `AGENTS.md` + native skills/rules —
tells an agent *how to behave*. MCP would give it **callable buttons**, usable by
Claude, Codex, Cursor-style agents, and any MCP-aware tool-calling system.

## Planned tools
- `run_scan(config)` — run a reach-scan; return summaries + run manifest.
- `validate_projection(path)` — check a Projection against the bucket/target
  consistency rule before it is used.
- `audit_manifest(run_dir)` — verify provenance and `MANIFEST.sha256`.
- `write_reproduction_note(run_dir)` — emit a manifest-backed note.

## Why this is the strong (but last) rung
Every reachscan artifact is already **provenance-stamped** (source, sampler,
seeds, mock-vs-real). So each tool returns self-caveating output — the honesty
contract is enforced at the **tool boundary**, not just the instruction layer.

## Why it's deferred
MCP is the most work and should follow evidence that the instruction layer is
useful. Build order: open-weights reproducible example → `AGENTS.md` → native
skills/rules → (only then) this server.
