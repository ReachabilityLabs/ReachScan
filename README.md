# reachscan

**A black-box instrument for measuring which answer-futures remain reachable from a committed LLM reasoning prefix.**

![tests](https://github.com/ReachabilityLabs/ReachScan/actions/workflows/ci.yml/badge.svg)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20808922.svg)](https://doi.org/10.5281/zenodo.20808922)

`reachscan` freezes a reasoning prefix, samples fresh continuations, and treats the
resulting distribution of terminal answers as a **future field**. It reports how much
of that field still lands on a target answer — and how that reachability changes as the
model commits deeper — under an explicit model, sampler, prefix, and answer-lens
contract. Endpoint accuracy collapses behavior into one label; `reachscan` measures the
*reachable distribution behind* that label, before the answer is exposed.

## What the instrument revealed

Using `reachscan`, the associated paper demonstrates a closed loop of **answer
foreclosure** — a designated answer goes from reachable to effectively foreclosed
*before it is expressed*, the transition can be localized, and the field can be reopened
and re-closed by different downstream paths:

```text
   reachable ──▶ foreclosed ──▶ corrected / reopened ──┬─▶ fresh path stays open
 (target alive)  (before the                           │
                  answer is written)                   └─▶ original path re-closes
```

That is the meaning of **existence is not reachability**: a target answer can be
reachable from one measured state, *effectively unreachable* from a committed wrong
state under the same rollout contract, and *reopenable* from a corrected state. The
contribution is the complete cycle — measure, discriminate, localize, perturb, remeasure
— not any single step, and it claims neither model-universal generality nor an internal
causal mechanism.

> **Repository scope.** This repo is the reusable measurement **core** — enough to
> understand the method and run a scan on your own model and task. The paper's grouped
> experiments, token-level localization, perturbation study, and canonical evidence live
> in the **Evidence and Reproducibility Archive**, not here.

## What the paper shows

On Qwen2.5-Math floor-sum reasoning, with this instrument:

- **Structural foreclosure (field level).** The prompt-only field is already biased
  toward a target-excluding arithmetic family; commitment depletes target-compatible
  mass *before* a particular wrong atom dominates, and the answer field becomes nearly
  fixed while surface reasoning stays diverse — closure of the correct region, selection
  of a wrong answer, and collapse of textual diversity are *three separable events*.
- **Diagnosticity (replicated).** Across 20 correct-source vs 20 wrong-source prefixes,
  the arms overlap at mid-depth but separate by **+0.732** at the deepest cut (D09); a
  disjoint-seed run reproduces the profile, and a prospectively selected same-family
  replication (D07) yields **+0.802** (95% trace-bootstrap CI **[+0.695, +0.894]**).
- **Pre-expression timing.** Token-level rescanning localizes foreclosure across 18
  wrong traces to a median **4.5-token** window, with a median **170-token** interval
  between the loss of target reach and the moment the answer is emitted.
- **Morphology.** A reach–entropy view distinguishes diffuse **shatter** from
  concentrated **capture** at similarly low target reach — target viability is *not* the
  same as entropy or answer concentration, which is why the full field is retained
  rather than reduced to one scalar.
- **Functional validation.** In five localized traces, a corrective splice reopens the
  target in **four**; matched and scrambled controls generally do not; fresh continuation
  preserves the repair through 32 tokens in **four**; and replaying the original
  downstream path re-closes it in **all five**.

The full argument and figures are in the paper (*Existence Is Not Reachability*); the
canonical data and constructors are in the Evidence and Reproducibility Archive. The
worked example in *this* repo **illustrates the readout shape** on a mock or small live
model — the committed demo is a mock fixture, not a result, and this is not a release of
the paper's production data.

> Status: v0.3.5 ([Zenodo](https://doi.org/10.5281/zenodo.20837723)). The engine and
> reference components are tested.

## Install

```bash
pip install -e .            # core, zero heavy dependencies (mock path)
pip install -e ".[hf]"      # add a real HuggingFace model source
pip install -e ".[projection]"  # add projection-pack support (PyYAML)
pip install -e ".[test]"    # run the tests
```

## Quick start (no GPU, mock source)

```bash
reachscan-demo --out demo_run
```

This runs a reach-scan with a **mock** source. It proves the pipeline end to end
and shows the readout format, but the mock is a deterministic fixture, **not a
real model** — the numbers are illustrative, not a result. For a real measurement,
point it at a model:

```bash
reachscan-demo --hf Qwen/Qwen2.5-Math-7B-Instruct --out qwen_run   # needs [hf] extra + GPU
```

For longer Colab/GPU runs, use
[`notebooks/reachscan_quickstart.ipynb`](notebooks/reachscan_quickstart.ipynb).
The notebook starts with an explicit run contract: no model is selected by
default, and the run cannot proceed until a tier, revision policy, claim ceiling,
and model-specific confirmation token agree. See
[`docs/CHOOSE_YOUR_RUN.md`](docs/CHOOSE_YOUR_RUN.md) before spending GPU time.
The notebook prints resource diagnostics, caches the generated reference trace,
and checkpoints each completed depth so a disconnected runtime can skip finished
depths on rerun while preserving the original depth indices and seed rule.

## What it measures

At the prompt-only state and at a series of committed-prefix depths, `reachscan`
samples futures, classifies each extracted answer through a **projection**, and
reports, per depth:

- **target reachability** `R_T(f)` — mass on the task's target set
- **dominant basin** and its mass — where the field concentrates
- **answer-field entropy** — a target-*neutral* dispersion statistic (distinct from
  target reachability, which is target-*relative*)
- **answer yield / truncation / cap-hits** — the denominator audit (`hit_token_cap` flags every generation that filled `max_new_tokens`). Reported as `ok_answers`; the legacy `numeric` column is kept as an alias through v0.3.x and means `status == "ok"` extracted answers, not necessarily numeric values.
- **Wilson intervals** on the rates

### Raw field vs projected field (read this once)

The measurement object is the **full terminal-answer distribution** (the paper's *full
answer tally*). Everything else is a *view* — a pushforward / coarse-graining — of it.
The repo keeps these distinct, and so should you:

- **raw answer field** — the distribution over actual extracted answers, reconstructable
  from `parsed_answer` / `value` in the per-rollout **receipts**.
- **projected field** — the declared bucket distribution in `summary_by_depth.csv`,
  produced by `projection.project(answer)` (residue classes under `ModuloProjection`,
  answer atoms under `ExactMatch`).
- **target-set readout** — mass on the declared target class (`R_T`).
- **exact-outcome rate** — mass on the exact accepted answer.

A projection is a coarse-graining; it never *replaces* the raw field. The paper's
shatter-vs-capture morphology only exists because the full field is retained, not
reduced to one scalar.

### Formal object

Let `s_f` be the prompt followed by the committed prefix at depth fraction `f`,
and let `T` be the task's target set (the correct answer, or its residue class).
The **future field** is the distribution of *successfully extracted* answers under
the declared sampler, conditioned on `s_f`. **Target reachability** is its mass on
the target, conditioned on a valid extraction:

```
R_T(f) = P( extract(Y) ∈ T | extract(Y) defined, committed prefix s_f, declared sampler )
```

The denominator is the **answer yield** — rollouts whose completion produced a
parseable answer (`status == "ok"`); rollouts with no extractable answer are
excluded from the denominator. Cap-hits (generations that filled
`max_new_tokens`) are flagged *independently* — a capped generation that still
produced a parseable answer is counted. When the yield is zero, `R_T` is
**undefined** (reported as `NaN`, with `rate_defined=False`), never zero.
Estimated by `M` independent rollouts per depth and reported with a Wilson
interval. `reachscan` estimates this conditional object — it is not a statement
about the model's internals.

## Scope

This repository is the public **reach-scan core**: the source interfaces, prefix
slicing, projection/target handling, future-field summaries, a mock fixture, a minimal
HuggingFace adapter, a custom-projection example, and a quickstart notebook — enough to
understand the method and run a basic scan on your own model and task.

This is the measurement **core**, not the paper's full reproduction workflow. It does
**not** include candidate mining, exposure auditing, grouped correct/wrong-source
scans, per-trace bootstrap, foreclosure localization, or intervention. The
current-paper evidence and constructors are released through the Evidence and
Reproducibility Archive; additional research tooling is outside this software
release.

## How it works: three contracts + an engine

The engine knows nothing about any specific model or task. It depends on three
small contracts; everything specific lives in implementations of them:

| Contract | Promise | Ships with |
|---|---|---|
| `TokenContinuationSource` | "given a committed prefix, yield sampled futures" | `MockSource`, `HuggingFaceSource` |
| `PrefixSource` | "yield a committed reference trace to slice by fraction" | `GeneratedPrefixSource`, `UserPrefixSource` |
| `Projection` | "classify an extracted answer into a task bucket" | `ExactMatch`, `ModuloProjection`, `TargetFiber` |

To measure **your** model on **your** task, you implement a source and/or a
projection. You never touch the engine.

`TokenContinuationSource` is the **repo's** concrete implementation of an abstract
"committed prefix → sampled futures" shape — the underlying resampling operation is
shared with prior work (see [Related work](#related-work)). The engine depends on that
shape, not on tokens as such; other substrates could be measured by implementing the
same shape, though none is provided here.

The shipped real-model source measures an **autoregressive, token-emitting model
you have token-level access to** — a local open-weights model (the typical
HuggingFace path), your own model, or a frontier model *if you hold its weights*.
The line is **token-level access, not public-vs-closed**: it needs to freeze a
committed prefix on token IDs and sample fresh continuations under a declared
sampler, which a hosted chat **API** (Claude/GPT endpoints) does not expose — so
the shipped tool can't run on an API model out of the box. The abstract contract
is substrate-general — other substrates (non-autoregressive / diffusion, agents)
could implement the same "committed state → reachable futures" shape — but those
are **research extensions, not provided or claimed here**; a closed-API adapter
would likewise be possible, with weaker reproducibility guarantees.

> **Using an AI coding agent on this repo?** See [`AGENTS.md`](AGENTS.md) and
> [`docs/agents/`](docs/agents/) for an operator guide that keeps measurements
> honest (no overclaiming, provenance preserved).

## The flagship example

The floor-sum case (correct answer 532; `532 % 8 == 4`) is simply:

```python
projection = ModuloProjection(8, target_residue=4)
```

The flagship is a *configuration* of the general instrument, not a special path.

## Projection packs (v0.3.0)

A **projection pack** makes a task lens executable and auditable: a directory that
declares the parser, the outcome check, the projection classes, and labeled
fixtures, fingerprinted by a **behavior-bearing** hash over its
`projection.yaml` + `adapter.py` + `fixtures.jsonl` (so a parser edit cannot keep
the same identity). The flagship as a pack lives in
[`examples/projections/floor_sum_mod8/`](examples/projections/floor_sum_mod8/).

```bash
pip install -e ".[projection]"
reachscan projection validate examples/projections/floor_sum_mod8
```

A loaded pack also satisfies the `Projection` protocol, so `reach_scan` runs it
directly; a pack-driven run binds the `projection_pack` block (id, version, hash,
declared classes, claim level, fixture-validation result) into `run_manifest.json`
and records `projection_class` + projection identity on every receipt. The engine
stays generic — a plain projection produces no pack block, and `engine_schema`
moved `0.2.8 → 0.3.0` only because receipts and the manifest grew.

Two floor-sum packs ship **built in** (resolvable by name from a pip install via
`reachscan.builtin_pack_path(...)`): `floor_sum_mod8` — the morphology lens
(target = residue-4 fiber), the claim-bearing default; and `floor_sum_exact` — a
companion sanity lens (target = exactly 532), exact-answer reachability.

To build a lens for **your own** task, copy
[`examples/projections/_template/`](examples/projections/_template/) and follow
[`docs/BUILD_A_PROJECTION_PACK.md`](docs/BUILD_A_PROJECTION_PACK.md).

The pack's predeclared `prediction` block is evaluated from raw receipts into a
`supported / failed / inconclusive` verdict:

```bash
reachscan prediction evaluate <run_dir> --projection examples/projections/floor_sum_mod8
```

The three tests read **wrong-answer morphology** (family structure, capture vs
shatter, family-before-atom); thin/zero evidence is `inconclusive`, never a false
support; and the evaluator refuses a run that used a different pack (it checks the
`projection_pack_hash`). See [`docs/PREDICTION_CONTRACT.md`](docs/PREDICTION_CONTRACT.md).

## Control surface

ReachScan is not one metric — it is an instrument with object-defining knobs,
measurement knobs, a reading lens, and claim gates. The figure below is the whole
control surface as a signal chain (substrate → probe → sample → read → judge):
what can be **chosen**, what gets **recorded**, and what gets **locked**.

![ReachScan control surface](docs/instrument_control_surface.svg)

> ReachScan becomes claim-bearing when the object, sampling conditions, projection
> lens, and prediction rule are declared before the run and then evaluated from raw
> receipts.

**Operating the instrument:** [`docs/RUN_PATH.md`](docs/RUN_PATH.md) is the
step-by-step procedure (research question → valid run → defensible claim), and
[`docs/CLAIM_LADDER.md`](docs/CLAIM_LADDER.md) is what each run is allowed to
support. The figure names the dials; those two turn it into a workflow.

Source: [`docs/instrument_control_surface.dot`](docs/instrument_control_surface.dot)
(regenerate with `dot -Tsvg docs/instrument_control_surface.dot -o docs/instrument_control_surface.svg`).

## Repo layout

```text
src/reachscan/
  contracts.py        # the three protocols + ExtractedAnswer (the frozen interfaces)
  engine.py           # the reach-scan engine (knows only the contracts)
  projections.py      # ExactMatch, ModuloProjection, TargetFiber
  prefix_sources.py   # GeneratedPrefixSource, UserPrefixSource
  mock_source.py      # zero-dependency test fixture (NOT a real model)
  hf_source.py        # HuggingFaceSource — the live path (optional [hf] extra)
  metadata.py         # provenance stamping + receipts/summary writers
  contrast.py         # source-conditioned separation (the diagnostic kernel)
  projection_pack.py  # v0.3.0 projection packs: load, behavior-bearing hash, fixtures
  prediction.py       # v0.3.1 prediction evaluator: morphology verdict from receipts
  tools/run_demo.py   # the reachscan-demo CLI
  tools/cli.py        # `reachscan projection validate|inspect` + `prediction evaluate`
examples/projections/floor_sum_mod8/   # the flagship as a formal projection pack
tests/
  test_engine.py      # engine correctness + seed/plan guards
  test_projection_pack.py  # pack load/hash/fixtures + receipt/manifest binding
  test_prediction.py       # prediction evaluator: fixtures + verification checks
  test_run_contract.py     # the notebook run-contract gate
```

## Use it on your own task

To measure a task that isn't floor-sum, implement a `Projection` — three methods:
`extract` (pull the answer from completion text), `project` (assign a bucket), and
`is_target` (does it hit the target set?). `examples/custom_projection.py` is a
complete, **non-arithmetic** one (multiple-choice A/B/C/D); run it with no GPU:

```bash
python examples/custom_projection.py
```

Swap your projection in and you are measuring reach-to-target on your task — you
never touch the engine.

## Diagnostic use: source-conditioned contrast

A single reach-scan measures one prefix. The diagnostic question is comparative:
do correct-source and wrong-source committed prefixes reach the target differently,
*before* the answer is exposed? Run a scan on each and contrast them:

```python
from reachscan import source_separation
sep = source_separation(correct_result, wrong_result)   # same depth plan on both
for row in sep:
    print(row.fraction, row.separation, (row.sep_low, row.sep_high))
```

`source_separation` returns the per-depth reachability separation with a Newcombe
confidence interval on the difference. See `examples/source_contrast.py`.

This is the diagnostic *primitive*. Getting labeled correct/wrong source traces, and
finding candidates where the separation is large, is the research: you supply your
own sources, and that apparatus is not included here.

## What reachscan is not

- It is **not** a probe of model internals. The field is a black-box behavioral
  distribution over outputs; it makes no claim about activations or hidden state.
- A **zero count is a finite-budget observation**, not a proof of zero
  probability. Every count is conditional on the declared sampler and on `M`.
- Two tasks in one model is **not** generality. Cross-model and cross-task
  portability are separate claims, earned by replication, not asserted here.

## Limitations

- **Reference extractor.** The shipped `extract` prefers the last `\boxed{...}`,
  strips thousands-commas, and otherwise looks for an explicit answer cue. It does
  not parse scientific notation, units, or symbolic answers, and the no-box
  fallback (last number) is unreliable. Watch the answer-yield column (`ok_answers`), and for
  other answer formats supply your own `extract`. This is a reference component,
  not a production extractor.
- **Cost.** Rollouts are generated one at a time for per-seed reproducibility, so
  large `M` on a real model is slow; batched generation is a future optimization.
- **Reproducibility.** Seeds reproduce the sampling decisions given identical
  logits; bitwise reproduction across different hardware or kernels is not
  guaranteed. Seeds are integers in `[0, 2**64)`; custom sources must accept the
  full range (do not feed them to 32-bit-only seeders).
- **HuggingFaceSource is a reference adapter, not a paper-grade backend.** It pins
  models via the optional `revision` argument, and it builds its decode policy as an
  EXPLICIT `GenerationConfig` from the declared `SamplerPolicy` alone — the model's own
  `generation_config` defaults (top_k, penalties) are **not** silently merged, and the
  run manifest records this under `sampler_semantics`. It still does not hash the chat
  template, record the tokenizer revision, batch, or capture finish reasons. Bring your
  own backend for paper-grade runs.
- **Truncation is typed; cap-hits are engine-flagged.** The source contract returns
  token IDs only, so the source-flagged `truncated` status requires a finish-reason-capable
  source. The engine independently flags `hit_token_cap` (generation length reached
  `max_new_tokens`) on every receipt and counts it per depth — the honest budget audit
  available without one. Finish reasons are planned for a future release as an *optional* source
  capability, never as a change to the required contract surface.

## Related work

`reachscan` builds directly on prefix-resampling and tokenwise outcome-distribution
work — Forking Paths and token-level "road not taken" uncertainty study alternate
futures from a state; Thought Anchors and Thought Branches resample around reasoning
steps to attribute final-answer effects; and a line of failure-prefix / recoverability /
process-supervision work (failure-prefix conditioning, ELPO, Deep Dense Exploration,
value/process-reward models) summarizes a prefix by a success *scalar* to train, search,
or localize errors. `reachscan` retains the **full answer field** instead of a scalar,
applies it to a **designated target's** sustained closure, and — in the paper — closes
the loop with fresh-path vs. original-tail reopening/reclosure. The closest black-box
analog, *The Point of No Return*, shares the same prefix-resampling primitive but
localizes *deceptive-outcome* probability rather than a designated target's reachability
and reopening; behavior-prediction-for-steering work such as *Predicting Future
Behaviors* instead operates white-box on internal representations (training activation
probes). It also sits alongside chain-of-thought faithfulness (Turpin et al. 2023;
Lanham et al. 2023), self-consistency (Wang et al. 2023), and process supervision
(Lightman et al. 2023).
See the paper's related-work section for the full treatment.

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE). Every output
artifact carries provenance metadata and a citation request; attribution is
requested per the NOTICE, not restricted beyond Apache-2.0.

## Citation

```bibtex
@software{nothem2026reachscan,
  author  = {Michael Richard Nothem},
  title   = {reachscan: a committed-prefix future-field measurement instrument},
  version = {0.3.5},
  year    = {2026},
  doi     = {10.5281/zenodo.20837723},
  url     = {https://github.com/ReachabilityLabs/ReachScan}
}
```

Cite the **version DOI** `10.5281/zenodo.20837723` to point at exactly v0.3.5; the
**concept DOI** `10.5281/zenodo.20808922` always resolves to the latest version.

## Associated research products

This software is one component of the *Existence Is Not Reachability* publication
family. The concise paper states the central scientific result; the Full Technical
Report contains the complete argument and audit record; the Evidence and
Reproducibility Archive contains the canonical evidence and constructors. See
`docs/PRODUCT_ARCHITECTURE.md` and `release_assets/release_manifest.json`.

It is also the language-model sibling of the oracle-backed random 3-SAT
[constructive-accessibility instrument](https://doi.org/10.5281/zenodo.19225548): the
two share one measurement grammar — **committed state → reachable future** — across a
stochastic language substrate and an exact combinatorial one. That shared grammar is the
broader Reachability Labs research program; this article does not depend on it for its
result.
