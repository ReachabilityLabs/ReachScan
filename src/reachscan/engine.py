"""reachscan engine — the frozen public core.

Knows ONLY the three contracts + ExtractedAnswer + the seed rule. No torch,
no floor-sum, no mod-8, no tokenizer. It performs the reach-scan measurement:
freeze committed prefixes at a set of depths, sample futures at each, classify
them through a Projection, and assemble the future field plus the standard
readouts (target reachability, dominant basin, answer-field entropy, yield,
Wilson intervals).
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Hashable, Sequence

from .contracts import (
    ExtractedAnswer,
    PrefixSource,
    Projection,
    SamplerPolicy,
    TokenContinuationSource,
)


# --------------------------------------------------------------------------
# Plan: per-depth rollout counts (contract patch R1 — M varies by depth)
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class DepthSpec:
    fraction: float                # prefix fraction in [0, 1] (the depth LABEL)
    rollouts: int                  # M at THIS depth
    committed_len: int | None = None
    # committed_len, when given, OVERRIDES round(fraction * L) as the resolved
    # committed-token count (contract v3 R5: a near-terminal anchor like the
    # paper's 99.9% row is specified by COUNT, e.g. L-1, with fraction kept as
    # the reported label). Receipts always record the resolved count.


def uniform_plan(fractions: Sequence[float], rollouts: int) -> list[DepthSpec]:
    """Broadcast one rollout count across many fractions (simple case)."""
    return [DepthSpec(float(f), int(rollouts)) for f in fractions]


# --------------------------------------------------------------------------
# Seed rule (contract patch R2 — collision-free at any M)
# --------------------------------------------------------------------------
def derive_seed(base_seed: int, depth_index: int, rollout_index: int) -> int:
    """Distinct (depth_index, rollout_index) -> distinct seed, no stride
    assumption, so M may be any size. Recorded in receipts for reproducibility."""
    key = f"{base_seed}|{depth_index}|{rollout_index}".encode()
    return int.from_bytes(sha256(key).digest()[:8], "big")


# --------------------------------------------------------------------------
# Result containers
# --------------------------------------------------------------------------
@dataclass
class RolloutReceipt:
    depth_index: int
    fraction: float
    committed_len: int
    rollout_index: int
    seed: int
    status: str
    value: str | None
    bucket: Hashable | None
    is_target: bool
    hit_token_cap: bool  # generation length reached max_new_tokens (cap-hit audit)


@dataclass
class DepthSummary:
    fraction: float
    committed_len: int
    attempts: int
    ok_answers: int              # status == "ok" extracted answers (the R_T denominator)
    numeric: int                 # legacy alias of ok_answers (v0.2.x); NOT necessarily numeric values
    truncated: int               # source-flagged truncations (needs a finish-reason-capable source)
    cap_hits: int                # engine-flagged: len(new tokens) >= max_new_tokens
    no_answer: int
    target_reachability: float   # R_T(f): mass on target among OK answers
    target_count: int
    dominant_bucket: Hashable | None
    dominant_mass: float
    answer_field_entropy: float  # target-NEUTRAL, over OK answers (no logits)
    wilson_target_low: float
    wilson_target_high: float
    field: dict                  # bucket -> count among OK answers


@dataclass
class ReachScanResult:
    summaries: list[DepthSummary] = field(default_factory=list)
    receipts: list[RolloutReceipt] = field(default_factory=list)
    manifest: dict = field(default_factory=dict)


# --------------------------------------------------------------------------
# Small stats helpers
# --------------------------------------------------------------------------
def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total <= 0:
        return (0.0, 0.0)
    p = successes / total
    denom = 1.0 + z * z / total
    centre = p + z * z / (2 * total)
    radius = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total)
    return ((centre - radius) / denom, (centre + radius) / denom)


def shannon_entropy_bits(counts: Sequence[int]) -> float:
    total = sum(counts)
    if total <= 0:
        return 0.0
    h = 0.0
    for c in counts:
        if c <= 0:
            continue
        p = c / total
        h -= p * math.log2(p)
    return h


# --------------------------------------------------------------------------
# The engine
# --------------------------------------------------------------------------
_ENGINE_SCHEMA_VERSION = "0.2.3"  # bumped: manifest plan rows gain resolved_committed_len


def reach_scan(
    *,
    source: TokenContinuationSource,
    prefix_source: PrefixSource,
    projection: Projection,
    plan: Sequence[DepthSpec],
    rollout_sampler: SamplerPolicy,
    base_seed: int = 0,
    stop_token_ids: Sequence[int] | None = None,
    include_prompt_only: bool = True,
) -> ReachScanResult:
    """Run a reach-scan. Every input is an explicit parameter or a named
    contract — there are no hidden inputs, and every input lands in the manifest.

    include_prompt_only: when True (default) and 0.0 is absent from the plan, the
    engine PREPENDS the prompt-only row (the paper's load-bearing f=0 field).
    depth_index in receipts indexes this EFFECTIVE plan — the user plan plus the
    prepended row when injected — and the effective plan is what the manifest
    records, so the numbering is never ambiguous."""
    prompt = list(prefix_source.prompt_ids())
    trace = list(prefix_source.reference_trace_ids())
    L = len(trace)
    if L <= 0:
        raise ValueError("reference_trace_ids() returned an empty trace; nothing to scan")

    # Fail-loud plan validation (a malformed plan must never measure silently).
    for d in plan:
        if not (0.0 <= d.fraction <= 1.0):
            raise ValueError(f"DepthSpec.fraction must be in [0, 1]; got {d.fraction}")
        if d.rollouts < 1:
            raise ValueError(f"DepthSpec.rollouts must be >= 1; got {d.rollouts}")
        if d.committed_len is not None and not (0 <= d.committed_len <= L):
            raise ValueError(
                f"DepthSpec.committed_len must be in [0, {L}]; got {d.committed_len}")

    fractions_present = {round(d.fraction, 6) for d in plan}
    full_plan = list(plan)
    if include_prompt_only and 0.0 not in fractions_present:
        full_plan = [DepthSpec(0.0, plan[0].rollouts if plan else 1)] + full_plan
    if not full_plan:
        raise ValueError("empty plan: provide at least one DepthSpec or include_prompt_only=True")

    result = ReachScanResult()
    for depth_index, spec in enumerate(full_plan):
        committed_len = (spec.committed_len if spec.committed_len is not None
                         else round(spec.fraction * L))
        committed = prompt + trace[:committed_len]

        answers: list[ExtractedAnswer] = []
        cap_flags: list[bool] = []
        for r in range(spec.rollouts):
            seed = derive_seed(base_seed, depth_index, r)
            new_ids = source.sample_completion(
                committed,
                temperature=rollout_sampler.temperature,
                top_p=rollout_sampler.top_p,
                top_k=rollout_sampler.top_k,
                repetition_penalty=rollout_sampler.repetition_penalty,
                max_new_tokens=rollout_sampler.max_new_tokens,
                stop_token_ids=stop_token_ids,
                seed=seed,
            )
            hit_cap = len(new_ids) >= rollout_sampler.max_new_tokens
            text = source.decode(new_ids)
            ans = projection.extract(text)
            answers.append(ans)
            cap_flags.append(hit_cap)

            bucket = projection.project(ans) if ans.is_ok else None
            tgt = projection.is_target(ans) if ans.is_ok else False
            result.receipts.append(
                RolloutReceipt(
                    depth_index=depth_index,
                    fraction=spec.fraction,
                    committed_len=committed_len,
                    rollout_index=r,
                    seed=seed,
                    status=ans.status,
                    value=ans.value,
                    bucket=bucket,
                    is_target=tgt,
                    hit_token_cap=hit_cap,
                )
            )

        result.summaries.append(
            _summarize_depth(spec, committed_len, answers, projection,
                             cap_hits=sum(cap_flags))
        )

    from . import __version__ as _pkg_version  # local import: avoid import-order fragility
    result.manifest = {
        "engine_schema": _ENGINE_SCHEMA_VERSION,
        "package_version": _pkg_version,
        "source": getattr(source, "name", "unknown"),
        "sampler_semantics": getattr(source, "sampler_semantics", None),
        "prefix_source": getattr(prefix_source, "name", "unknown"),
        "prefix_source_provenance": getattr(prefix_source, "provenance", None),
        "projection": getattr(projection, "name", "unknown"),
        "trace_len": L,
        "base_seed": base_seed,
        "rollout_sampler": vars(rollout_sampler),
        "stop_token_ids": list(stop_token_ids) if stop_token_ids else None,
        "include_prompt_only": include_prompt_only,
        "plan": [{"fraction": d.fraction, "rollouts": d.rollouts,
                  "committed_len": d.committed_len,
                  "resolved_committed_len": (
                      d.committed_len if d.committed_len is not None
                      else round(d.fraction * L))}
                 for d in full_plan],
        "seed_rule": "sha256(base_seed|depth_index|rollout_index)[:8]; seeds in [0, 2**64)",
    }
    return result


def _summarize_depth(
    spec: DepthSpec,
    committed_len: int,
    answers: list[ExtractedAnswer],
    projection: Projection,
    *,
    cap_hits: int = 0,
) -> DepthSummary:
    attempts = len(answers)
    ok = [a for a in answers if a.is_ok]
    truncated = sum(1 for a in answers if a.status == ExtractedAnswer.TRUNCATED)
    no_answer = sum(1 for a in answers if a.status == ExtractedAnswer.NO_ANSWER)

    # Future field: distribution over buckets among OK answers only. Single pass
    # ENFORCES the binding Projection consistency rule (contracts.py): a bucket
    # must not hold both target and non-target answers, or target reachability
    # would be incoherent. A bad custom projection fails loud and local here.
    field_counter: Counter = Counter()
    bucket_targets: dict[Hashable, bool] = {}
    target_count = 0
    _missing = object()
    for a in ok:
        bucket = projection.project(a)
        is_tgt = projection.is_target(a)
        previous = bucket_targets.get(bucket, _missing)
        if previous is not _missing and previous != is_tgt:
            raise ValueError(
                "Projection consistency violation: bucket "
                f"{bucket!r} contains both target and non-target answers "
                f"(projection={getattr(projection, 'name', projection)!r}). "
                "is_target must be a property of project()'s bucket."
            )
        bucket_targets[bucket] = is_tgt
        field_counter[bucket] += 1
        target_count += int(is_tgt)
    numeric = len(ok)
    r_t = (target_count / numeric) if numeric > 0 else 0.0

    if field_counter:
        dominant_bucket, dominant_n = max(field_counter.items(), key=lambda kv: kv[1])
        dominant_mass = dominant_n / numeric
    else:
        dominant_bucket, dominant_mass = None, 0.0

    entropy = shannon_entropy_bits(list(field_counter.values()))
    lo, hi = wilson_interval(target_count, numeric)

    return DepthSummary(
        fraction=spec.fraction,
        committed_len=committed_len,
        attempts=attempts,
        ok_answers=numeric,
        numeric=numeric,
        truncated=truncated,
        cap_hits=cap_hits,
        no_answer=no_answer,
        target_reachability=r_t,
        target_count=target_count,
        dominant_bucket=dominant_bucket,
        dominant_mass=dominant_mass,
        answer_field_entropy=entropy,
        wilson_target_low=lo,
        wilson_target_high=hi,
        field=dict(field_counter),
    )
