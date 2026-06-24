# Claim ladder

What a reach-scan run is allowed to support. This is the **spine** of the
instrument's honesty discipline: every run sits on exactly one rung, and the rung
is set by **how the run was designed**, not by which model you happened to use.

> **Two independent axes.** *Which model/task* you run (the substrate) is separate
> from *what you may claim* (the rung). A 7B model run carelessly is still rung 0;
> a small model run with predeclaration, pinning, exposure auditing, and adequate
> sampling can reach rung 2. Size does not buy a rung — design does.

The rung names below are the projection pack's `claim_level` values. A run-contract
**tier** is just a preset that *targets* a rung (see the mapping at the end).

## The rungs

### Rung 0 — Pipeline check  (`claim_level: smoke` / `pipeline_validation`)
- **Supports:** the code runs end to end; artifacts have the right shape;
  extraction/yield behaves.
- **Does NOT support:** any statement about a model's behavior. A `MockSource` run
  lives here permanently — a fixture is not a result.
- **Exposure ledger:** optional.

### Rung 1 — Morphology demonstration  (`claim_level: morphology_demo`)
- **Supports:** "on *this* model + task + sampler + projection, the future field
  shows shape X" — as an *illustration*, with a predeclared prediction verdict
  (`supported`/`failed`/`inconclusive`) computed from receipts.
- **Does NOT support:** that the shape is robust, replicated, or general.
- **Exposure ledger:** recommended.

### Rung 2 — Model-specific observation  (`claim_level: bounded_scientific_measurement`)
- **Supports:** a bounded, **predeclared, revision-pinned** measurement on one
  model and one task, with the prediction verdict, an adequate rollout budget `M`,
  and an **exposure ledger** (the answer was not already visible in the prefix).
- **Does NOT support:** cross-model or cross-task generality.
- **Exposure ledger:** **required.**

### Rung 3 — Cross-model / cross-task evidence  (`claim_level: cross_model_measurement` / `cross_task_measurement`)
- **Supports:** the *same* projection + prediction holding across several models
  (or several task families, each with its own validated pack). A step *toward*
  generality.
- **Does NOT support:** a generality law — it is a finite set of data points.
- **Exposure ledger:** **required** on every arm.

### Rung 4 — Generality  (`claim_level: generality_claim`)
- **Requires:** many models **and** task families, all predeclared and
  exposure-audited, with the morphology holding broadly.
- **Status:** aspirational — the public tool's worked examples do not reach this
  rung, and the current paper does not claim it.

## Binding honesty rules

1. A `MockSource` run never rises above rung 0.
2. One model + one task never rises above rung 2, no matter how clean.
3. An `inconclusive` (or zero-yield) verdict cannot be upgraded to support — fix
   the yield and rerun.
4. The verdict is a *declared read of the receipts*, not the receipts; the rung is
   claimed against the **raw artifacts**, never against a summary.
5. Exposure is a rung gate: rung 2 and above require the exposure ledger fields.

## Run-contract tiers → rungs (presets, not separate vocabulary)

| Run-contract tier (which model) | Typical rigor | Targets rung |
|---|---|---|
| `smoke` (Qwen-1.5B) | `smoke_budget` | Rung 0 |
| `paper_family` (Qwen2.5-Math-7B) | `research` (pinned, predeclared) | Rung 2 on the paper family |
| `cross_family` (Llama-3.1-8B) | `research` | Rung 2 on a second model → contributes toward Rung 3 |
| `custom` | depends | set by how it is designed |

A tier never *grants* a rung on its own — it only sets up a run that can reach one
once the predeclaration, pinning, exposure, sampling budget, and prediction verdict
are all in place. See [`RUN_PATH.md`](RUN_PATH.md) for the procedure and
[`CHOOSE_YOUR_RUN.md`](CHOOSE_YOUR_RUN.md) for picking a tier.
