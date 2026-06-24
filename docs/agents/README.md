# Agent support

ReachScan ships an **agent-onboarding layer** so a researcher can open the repo in
an AI coding agent (Claude Code, Codex, Cursor, or any MCP-aware tool) and have it
immediately understand: *this is a measurement instrument — run it carefully,
don't overclaim, preserve provenance.*

## Layers

```text
Paper            why this matters (the narrow, honest scientific claim)
Repo / engine    the measurement core (src/reachscan, tests, examples)
AGENTS.md        shared baseline — read natively by Codex, Cursor, and other
                 AGENTS.md-aware tools
Skills / rules   native per-tool onboarding (Claude / Codex / Cursor) — all THIN
MCP              portable, callable tools across agents (planned; see mcp/README.md)
```

There is **one canonical source of truth** plus thin per-dialect adapters (DRY):
the workflow is written once, in `docs/agents/reachscan-operator.md`, and every
wrapper inlines the honesty contract and points there. No dialect is the "center."

## What's here

| Path | Dialect | Role |
|---|---|---|
| `docs/agents/reachscan-operator.md` | canonical (all) | single source of truth |
| `docs/agents/templates/` · `docs/agents/reference/` | shared, dialect-neutral | templates + field reference (verified against the live engine) |
| `AGENTS.md` | shared baseline (Codex, Cursor, …) | repo-root baseline |
| `.claude/skills/reachscan-review/SKILL.md` | Claude Code | thin adapter |
| `.agents/skills/reachscan-review/SKILL.md` | Codex | thin adapter |
| `.cursor/rules/reachscan-review.mdc` | Cursor | thin adapter |
| `mcp/README.md` | MCP | planned interface (not yet implemented) |

The shared **templates + reference** live once, in the dialect-neutral
`docs/agents/`, and all three wrappers point there.

## Honest caveats

- **The compute barrier doesn't move.** These wrappers lower the *instruction*
  barrier so any agent understands the tool. Real measurements still need model
  access; the no-GPU parts (projection design, interpreting shipped artifacts,
  auditing) are what anyone can do without a model.
- **Open-weights only, by design.** The shipped real-model path runs a local
  open-weights model (HuggingFace); closed/API chat models can't be used out of the
  box (the contract needs token-level prefix continuation). This is stated in
  `AGENTS.md`, the canonical guide, and the root `README.md`.
- **Tool-detection status.** Confirmed: Codex scans `.agents/skills/` and its
  `SKILL.md` needs only `name`+`description`; Cursor uses `.cursor/rules/*.mdc` and
  also reads `AGENTS.md`; `AGENTS.md` is a cross-tool standard. Not independently
  confirmed here: tools beyond Codex/Cursor (e.g. Copilot) and the exact `.mdc`
  frontmatter field set (`description`/`globs`/`alwaysApply`) — re-confirm against
  current vendor docs before relying on them.
