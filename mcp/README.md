# MCP layer (planned)

**MCP support is not implemented yet; this document records the intended
interface.** The instruction layer (`AGENTS.md` + native skills/rules) tells an
agent *how to behave*. An MCP server would add **callable tools**, usable by
Claude, Codex, Cursor-style agents, and any MCP-aware tool-calling system.

## Planned tools
- `run_scan(config)` — run a reach-scan; return summaries + run manifest.
- `validate_projection(path)` — check a Projection against the bucket/target
  consistency rule before it is used.
- `audit_manifest(run_dir)` — verify provenance and `MANIFEST.sha256`.
- `write_reproduction_note(run_dir)` — emit a manifest-backed note.

## Why a tool boundary helps
Every reachscan artifact is already **provenance-stamped** (source, sampler,
seeds, mock-vs-real), so each tool would return self-caveating output — the honesty
contract enforced at the **tool boundary**, not only the instruction layer.

## Roadmap
MCP is the most involved layer and is intended to follow evidence that the
instruction layer is useful: a reproducible open-weights example, then `AGENTS.md`,
then the native skills/rules, then this server.
