# Reach-scan reproduction note

> Fill every field from the run's `run_manifest.json` and `summary_by_depth.csv`.
> If a value isn't traceable to a named input in the manifest, do not report it.

## What was measured
- **Source:** <e.g. hf:Org/Model@revision  —  or MOCK FIXTURE (not a result)>
- **Is this a real measurement?** <yes / NO — mock fixture, illustrative only>
- **Task & target:** <one line; what set T counts as the target>
- **Projection:** <name, e.g. ModuloProjection(8, target_residue=4)>
- **Prefix source:** <generated_trace (trace_seed, trace_sampler) / user_trace>

## Declared sampler (rollouts)
- temperature / top_p / top_k / repetition_penalty / max_new_tokens: <...>
- `sampler_semantics`: <verbatim from manifest, e.g. explicit-generation-config>
- base_seed: <...>   seed_rule: <verbatim from manifest>
- include_prompt_only: <true/false>   M (rollouts per depth): <...>

## Depth plan
| fraction | resolved_committed_len | rollouts |
|---|---|---|
| <...> | <...> | <...> |

## Result
| depth (f) | ok_answers | R_T | Wilson [low, high] | dominant basin (mass) | entropy | cap_hits | truncated |
|---|---|---|---|---|---|---|---|
| <...> | <...> | <...> | <...> | <...> | <...> | <...> | <...> |

**Reading:** <describe the depth TREND, e.g. "R_T falls from X to Y as commitment
deepens while basin mass rises to Z — a foreclosure shape." State it as the
trend, not a single number.>

## Honesty caveats (keep all that apply)
- This is a finite-budget (M=<...>), sampler-relative, projection-relative
  estimate of a conditional behavioral object; a zero/low count is an
  observation under this budget, not a proof of zero probability.
- It is a black-box output distribution; it makes no claim about model internals.
- This is one source on one task; it is not a cross-model or cross-task claim.
- <if mock> These numbers are fixture output and are NOT a measurement.

## Reproduce
```bash
pip install -e ".[hf]"        # or "." for the mock path
reachscan-demo --hf <MODEL_ID> --out <run_dir> --M <M> --seed <seed>
sha256sum -c MANIFEST.sha256       # integrity (Linux); macOS: shasum -a 256 -c MANIFEST.sha256
```
- Package version / engine schema: <package_version> / <engine_schema>
- Note: seeds reproduce sampling decisions given identical logits; bitwise
  reproduction across different hardware/kernels is not guaranteed.
