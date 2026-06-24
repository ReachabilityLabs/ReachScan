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
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from typing import Callable, Hashable, Sequence

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
    n_new_tokens: int = 0  # generated-token count for THIS rollout (deterministic cost)
    # --- v0.3.0 projection-pack binding (None/defaults when no pack is used) ---
    projection_class: str | None = None   # the declared class (residue_4 / no_answer / invalid)
    parsed_answer: str | None = None       # = value; the spec's parsed_answer column
    target_hit: bool = False               # outcome check (exact correct answer), distinct from is_target
    parse_status: str = "ok"               # ok | no_answer | truncated | invalid
    projection_id: str | None = None
    projection_version: str | None = None
    projection_pack_hash: str | None = None
    source_arm: str | None = None
    answer_exposed_in_prefix: bool | None = None
    exposure_check_id: str | None = None
    exposure_check_status: str = "not_checked"
    raw_completion: str = ""               # raw model text (the spec's raw_completion evidence)


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
    target_reachability: float   # R_T(f): mass on target among OK answers (NaN if ok_answers == 0)
    rate_defined: bool           # False when ok_answers == 0 -> R_T/Wilson are undefined (NaN)
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
# Cost instrumentation (v0.2.8). The engine MEASURES; callers PRESENT. Two tiers,
# never conflated: WORK (generated tokens) is deterministic given seed+model;
# ENVIRONMENT (wall-clock, hardware) is noisy provenance, not a measurement.
# The engine never imports torch — hardware identity comes FROM the source.
# --------------------------------------------------------------------------
def _safe_runtime(source) -> dict | None:
    """Ask the source to describe its runtime (device, GPU, versions). Optional:
    a source without describe_runtime contributes None, and a source that raises
    cannot abort a scan. Keeps the engine substrate-agnostic (no torch here)."""
    fn = getattr(source, "describe_runtime", None)
    if not callable(fn):
        return None
    try:
        return fn()
    except Exception as exc:  # a misbehaving source must not kill the run
        return {"error": repr(exc)}


def _cost_block(gen_tokens_by_depth: dict[str, int],
                wall_clock_by_depth: dict[str, float],
                runtime: dict | None,
                started_utc: str, ended_utc: str) -> dict:
    """Assemble the cost record. `work` is reproducible; `environment` is not."""
    return {
        "work": {
            "gen_tokens_total": sum(gen_tokens_by_depth.values()),
            "gen_tokens_by_depth": dict(gen_tokens_by_depth),
        },
        "environment": {
            "wall_clock_s_total": round(sum(wall_clock_by_depth.values()), 6),
            "wall_clock_s_by_depth": dict(wall_clock_by_depth),
            "runtime": runtime,
            "started_utc": started_utc,
            "ended_utc": ended_utc,
        },
    }


def estimate_cost(plan: Sequence[DepthSpec], *, seconds_per_token: float,
                  max_new_tokens: int, include_prompt_only: bool = True) -> dict:
    """Rough a-priori cost estimate for a plan. The rollout COUNT is exact; the
    SECONDS are an UPPER bound and a calibrated guess — label any printed number
    'estimated'. `seconds_per_token` is typically measured by timing the
    reference-trace generation. The bound assumes every rollout fills
    max_new_tokens and uses the trace-generation token rate, so it ignores the
    extra prefill cost at deeper prefixes; actual cost is lower when rollouts stop
    early. Prefer refining this live once depth 0 has really run (see the cost
    block in the result manifest)."""
    fractions_present = {round(d.fraction, 6) for d in plan}
    prepend = include_prompt_only and 0.0 not in fractions_present and bool(plan)
    total_rollouts = sum(d.rollouts for d in plan) + (plan[0].rollouts if prepend else 0)
    max_gen_tokens = total_rollouts * int(max_new_tokens)
    return {
        "total_rollouts": total_rollouts,
        "max_gen_tokens": max_gen_tokens,
        "seconds_per_token": float(seconds_per_token),
        "upper_bound_seconds": max_gen_tokens * float(seconds_per_token),
        "basis": ("UPPER bound: assumes every rollout fills max_new_tokens at the "
                  "trace-generation token rate; ignores deeper-prefix prefill. "
                  "Actual is lower if rollouts stop early — refine live after depth 0."),
    }


# --------------------------------------------------------------------------
# The engine
# --------------------------------------------------------------------------
_ENGINE_SCHEMA_VERSION = "0.3.0"  # + projection-pack receipt columns + manifest projection block


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
    run_depth_indices: Sequence[int] | None = None,
    source_arm: str = "natural_trace",
    on_depth_complete: Callable[[ReachScanResult], None] | None = None,
    on_progress: Callable[[dict], None] | None = None,
) -> ReachScanResult:
    """Run a reach-scan. Every input is an explicit parameter or a named
    contract — there are no hidden inputs, and every input lands in the manifest.

    include_prompt_only: when True (default) and 0.0 is absent from the plan, the
    engine PREPENDS the prompt-only row (the paper's load-bearing f=0 field).
    depth_index in receipts indexes this EFFECTIVE plan — the user plan plus the
    prepended row when injected — and the effective plan is what the manifest
    records, so the numbering is never ambiguous.

    run_depth_indices: optional subset of effective-plan depth indices to
    execute, preserving the original depth_index values and seed rule. This is
    for checkpoint/resume workflows; default behavior runs every depth.

    on_depth_complete: optional callback invoked after each completed depth with
    the current partial ReachScanResult (whose manifest already carries the
    running cost block). The callback must not mutate the result.

    on_progress: optional callback invoked after EACH rollout with a small dict
    ({depth_index, rollout_index, rollouts_in_depth, depths_total}); the notebook
    wraps it in a progress bar. Default None keeps the library silent."""
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

    selected_depths: set[int] | None = None
    if run_depth_indices is not None:
        selected_depths = {int(i) for i in run_depth_indices}
        invalid = sorted(i for i in selected_depths if i < 0 or i >= len(full_plan))
        if invalid:
            raise ValueError(
                f"run_depth_indices out of range for effective plan length "
                f"{len(full_plan)}: {invalid}"
            )
        if not selected_depths:
            raise ValueError("run_depth_indices must not be empty when provided")

    from . import __version__ as _pkg_version  # local import: avoid import-order fragility
    manifest = {
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
        "source_arm": source_arm,
    }
    # v0.3.0: bind a projection pack's declared lens into the manifest when present.
    # The engine stays generic — a plain Projection has no pack_meta and the block
    # is simply absent. `projection` (the name string) is kept for back-compat.
    pack_meta = getattr(projection, "pack_meta", None)
    if isinstance(pack_meta, dict):
        manifest["projection_pack"] = dict(pack_meta)
    if selected_depths is not None:
        manifest["executed_depth_indices"] = sorted(selected_depths)

    # Per-receipt projection identity (constants) + whether the projection offers
    # an outcome check distinct from target-class membership.
    _proj_id = pack_meta.get("projection_id") if isinstance(pack_meta, dict) else None
    _proj_ver = pack_meta.get("projection_version") if isinstance(pack_meta, dict) else None
    _proj_hash = pack_meta.get("projection_pack_hash") if isinstance(pack_meta, dict) else None
    _has_is_correct = isinstance(pack_meta, dict) and callable(
        getattr(projection, "is_correct", None)) and callable(getattr(projection, "parse", None))

    runtime = _safe_runtime(source)
    gen_tokens_by_depth: dict[str, int] = {}
    wall_clock_by_depth: dict[str, float] = {}
    started_utc = datetime.now(timezone.utc).isoformat()

    def _manifest_with_cost() -> dict:
        m = dict(manifest)
        m["cost"] = _cost_block(gen_tokens_by_depth, wall_clock_by_depth, runtime,
                                started_utc, datetime.now(timezone.utc).isoformat())
        return m

    result = ReachScanResult()
    result.manifest = dict(manifest)
    for depth_index, spec in enumerate(full_plan):
        if selected_depths is not None and depth_index not in selected_depths:
            continue

        committed_len = (spec.committed_len if spec.committed_len is not None
                         else round(spec.fraction * L))
        committed = prompt + trace[:committed_len]

        answers: list[ExtractedAnswer] = []
        cap_flags: list[bool] = []
        depth_tokens = 0
        depth_t0 = time.perf_counter()
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
            n_new = len(new_ids)
            depth_tokens += n_new
            hit_cap = n_new >= rollout_sampler.max_new_tokens
            text = source.decode(new_ids)
            ans = projection.extract(text)
            answers.append(ans)
            cap_flags.append(hit_cap)

            bucket = projection.project(ans) if ans.is_ok else None
            tgt = projection.is_target(ans) if ans.is_ok else False

            # v0.3.0 projection readout for the receipt. projection_class is the
            # declared class; target_hit is the exact OUTCOME check (distinct from
            # is_target, which is target-CLASS membership) when the projection
            # offers one. A plain projection falls back to is_target.
            if ans.is_ok:
                proj_class = str(bucket)
                if _has_is_correct:
                    try:
                        target_hit = bool(projection.is_correct(projection.parse(text)))
                    except Exception:
                        target_hit = tgt
                else:
                    target_hit = tgt
                parse_status = "invalid" if proj_class == "invalid" else "ok"
            else:
                proj_class = ans.status           # no_answer / truncated
                target_hit = False
                parse_status = ans.status

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
                    n_new_tokens=n_new,
                    projection_class=proj_class,
                    parsed_answer=ans.value,
                    target_hit=target_hit,
                    parse_status=parse_status,
                    projection_id=_proj_id,
                    projection_version=_proj_ver,
                    projection_pack_hash=_proj_hash,
                    source_arm=source_arm,
                    answer_exposed_in_prefix=None,
                    exposure_check_id=None,
                    exposure_check_status="not_checked",
                    raw_completion=text,
                )
            )
            if on_progress is not None:
                on_progress({
                    "depth_index": depth_index,
                    "rollout_index": r,
                    "rollouts_in_depth": spec.rollouts,
                    "depths_total": len(full_plan),
                })

        gen_tokens_by_depth[str(depth_index)] = depth_tokens
        wall_clock_by_depth[str(depth_index)] = round(time.perf_counter() - depth_t0, 6)
        result.summaries.append(
            _summarize_depth(spec, committed_len, answers, projection,
                             cap_hits=sum(cap_flags))
        )
        result.manifest = _manifest_with_cost()
        if on_depth_complete is not None:
            on_depth_complete(result)

    result.manifest = _manifest_with_cost()
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
    rate_defined = numeric > 0
    # Zero valid answers => the rate has no denominator. Report NaN (undefined),
    # NOT 0.0 — otherwise total extractor failure masquerades as certain zero
    # reachability, and source_separation would contrast undefined rows.
    r_t = (target_count / numeric) if rate_defined else float("nan")

    if field_counter:
        dominant_bucket, dominant_n = max(field_counter.items(), key=lambda kv: kv[1])
        dominant_mass = dominant_n / numeric
    else:
        dominant_bucket, dominant_mass = None, 0.0

    entropy = shannon_entropy_bits(list(field_counter.values()))
    lo, hi = (wilson_interval(target_count, numeric) if rate_defined
              else (float("nan"), float("nan")))

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
        rate_defined=rate_defined,
        target_count=target_count,
        dominant_bucket=dominant_bucket,
        dominant_mass=dominant_mass,
        answer_field_entropy=entropy,
        wilson_target_low=lo,
        wilson_target_high=hi,
        field=dict(field_counter),
    )
