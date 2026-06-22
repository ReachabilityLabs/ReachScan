# Interpreting reach-scan output

Loaded on demand. Field-by-field meaning of a run's artifacts, plus the traps.

## `summary_by_depth.csv` — one row per depth
| column | meaning | how to read it |
|---|---|---|
| `fraction` | depth label f in [0,1] (the reported depth) | the x-axis of the foreclosure curve |
| `committed_len` | resolved committed-token count at this depth | how many trace tokens were frozen |
| `attempts` | M rollouts attempted at this depth | the raw denominator before status filtering |
| `ok_answers` | count with status == "ok" (the R_T denominator) | **watch this** — a low value means the extractor failed, not that the model is unreachable |
| `numeric` | legacy alias of `ok_answers` (v0.2.x) | same number; kept for back-compat |
| `truncated` | source-flagged truncations | needs a finish-reason-capable source; often 0 |
| `cap_hits` | generations that filled `max_new_tokens` | **watch this** — high cap_hits means answers were cut off; the budget audit |
| `no_answer` | count with status == "no_answer" | extractor found nothing |
| `target_reachability` | R_T(f): target mass among OK answers (`NaN` if `ok_answers == 0`) | the headline, but report it WITH the interval and the trend |
| `rate_defined` | 0 when `ok_answers == 0` (R_T/Wilson are `NaN`) | **if 0, no valid answers at that depth — undefined, NOT zero reachability** |
| `target_count` | OK answers in the target set | numerator of R_T |
| `dominant_bucket` | the most massive bucket | where the field concentrates |
| `dominant_mass` | its share of OK answers | rising dominant mass + falling R_T = basin takeover |
| `answer_field_entropy` | bits over OK buckets (target-NEUTRAL) | dispersion; distinct from R_T (target-relative) |
| `wilson_target_low/high` | 95% Wilson interval on R_T | **always quote this** — never report R_T as a point |
| `field` | bucket -> count, serialized as a JSON object string | the full future field |

## Reading it well
- **Describe the trend, not a number.** Foreclosure = R_T falls as f grows while
  dominant_mass rises. A single depth in isolation says little.
- **Check the denominator first.** If `ok_answers` is small relative to
  `attempts`, the extractor is failing — fix `extract` before trusting R_T.
- **Check the budget.** Non-zero `cap_hits` means some generations were truncated
  at `max_new_tokens`; raise the budget or note it.
- **R_T vs entropy are different axes.** R_T is target-relative; entropy is
  target-neutral dispersion. A field can be low-entropy (concentrated) yet
  off-target.

## `receipts.csv` — one row per rollout
`depth_index, fraction, committed_len, rollout_index, seed, status, value,
bucket, is_target, hit_token_cap`. This is the per-rollout audit trail; the seed
column is what makes a single draw reproducible. `hit_token_cap` is the
per-receipt cap flag summed into `cap_hits`.

## `run_manifest.json` — the named inputs
Confirm every reported number traces to these keys: `source`,
`sampler_semantics`, `prefix_source` + `prefix_source_provenance`, `projection`,
`trace_len`, `base_seed`, `rollout_sampler` (full policy), `stop_token_ids`,
`include_prompt_only`, `plan` (each row has `fraction`, `rollouts`,
`committed_len`, `resolved_committed_len`), `seed_rule`, `package_version`,
`engine_schema`. The companion `.meta.json` carries provenance + citation.
Verify tree integrity with `sha256sum -c MANIFEST.sha256` (Linux) or
`shasum -a 256 -c MANIFEST.sha256` (macOS).

## Source contrast (`source_separation`)
Per-depth `separation = R_T(correct) - R_T(wrong)` with a Newcombe difference
interval (`sep_low`, `sep_high`). Both scans MUST share the same ordered depth
plan (fraction and resolved committed_len) — the engine rejects mismatches. A
separation interval that excludes 0 at a depth is the diagnostic signal; one that
includes 0 is not.
