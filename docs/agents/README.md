# ReachScan agent-instruction infrastructure

This is the **agent-onboarding layer** for ReachScan. It lets a researcher open
the repo in Claude Code, Codex, or Cursor and have the agent immediately
understand: *this is a measurement instrument; run it carefully; don't overclaim;
preserve provenance.*

It is a **draft for review**, staged outside the repo. The paths below are the
real target locations: merge the bundle's contents into the repo so that
`AGENTS.md` lands at the repo root, `docs/agents/` (including this README) lands
under `docs/`, and the `.claude/`, `.agents/`, `.cursor/` dirs merge in. **Do not
overwrite the repo's root `README.md`** — this file lives at `docs/agents/README.md`.

## The hierarchy (converged)

```text
Paper            why this matters (the narrow, honest scientific claim)
Repo / engine    the measurement core (src/reachscan, tests, examples)
AGENTS.md        shared baseline — read natively by Codex, Cursor, and other AGENTS.md-aware tools
Skills / rules   native per-tool onboarding (Claude / Codex / Cursor) — all THIN
MCP (planned)    portable, callable tools across agents
```

One **canonical source of truth** + thin per-dialect adapters (DRY): edit the
workflow once, in `docs/agents/reachscan-operator.md`; every wrapper inlines the
honesty contract and points there.

## What's in this bundle

| Path | Dialect | Status |
|---|---|---|
| `docs/agents/reachscan-operator.md` | canonical (all) | **built** — single source of truth |
| `docs/agents/templates/` · `docs/agents/reference/` | shared, dialect-neutral | **built** (template verified against the live engine) |
| `AGENTS.md` | shared baseline (Codex, Cursor, …) | **built** |
| `.claude/skills/reachscan-review/SKILL.md` | Claude Code | **built** — thin adapter |
| `.agents/skills/reachscan-review/SKILL.md` | Codex (`.agents/skills`) | **built** — thin adapter |
| `.cursor/rules/reachscan-review.mdc` | Cursor (`.cursor/rules`) | **built** — thin adapter |
| `mcp/README.md` | MCP (cross-agent tools) | **planned** — placeholder only |
| `docs/agents/README.md` | this file | bundle/architecture doc |

The shared **templates + reference** live once, in the dialect-neutral
`docs/agents/`, and all three wrappers point there — no dialect is the "center."

## Recommended build order (priority)

1. **An open-weights reproducible example** — the real keystone: a non-mock,
   pinned scan a stranger can run end-to-end and get a faithful result. (Not in
   this bundle; it's the substance the wrappers package.)
2. `AGENTS.md` (covers the Codex + Cursor baseline for free).
3. The thin per-tool wrappers (here; all built).
4. The MCP server (last).

## Honest caveats

- **The compute barrier doesn't move.** These wrappers lower the *instruction*
  barrier so any agent "gets it." Real measurements still need model access; the
  no-GPU parts (projection design, interpreting shipped artifacts, auditing) are
  what anyone can do without a model.
- **Open-weights only, by design.** The shipped real-model path runs a local
  open-weights model (HuggingFace); closed/API chat models can't be used out of
  the box (the contract needs token-level prefix continuation). This is stated in
  `AGENTS.md` and the canonical guide. **Also add a one-line, human-facing version
  to the repo's root `README.md`** (not in this bundle) so a casual visitor isn't
  surprised.
- **Verification status.** Directly confirmed: Codex scans `.agents/skills/` and
  its `SKILL.md` needs only `name`+`description`; Cursor uses `.cursor/rules/*.mdc`
  and also reads `AGENTS.md`; `AGENTS.md` is a cross-tool standard. *Not
  independently confirmed here:* specific tools beyond Codex/Cursor (e.g. Copilot)
  and the exact `.mdc` frontmatter field set (`description`/`globs`/`alwaysApply`)
  — re-confirm against current vendor docs before relying on them.
- **Gated by going public.** This layer only matters once the repo is public and
  the paper is deposited; it runs parallel to, and does not block, the science.
