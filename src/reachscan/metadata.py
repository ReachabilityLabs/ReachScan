"""Provenance stamping + receipts/summary writers.

Mirrors the SAT repo's metadata.py discipline: every output artifact carries a
companion .meta.json with framework tag, citation, usage notice, and timestamp.
This is attribution-in-the-artifact, the same pattern the CAI/SAT repo uses.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

FRAMEWORK_NAME = "Reachability Labs reachscan v0.2.9"
FRAMEWORK_TAG = "Nothem Reachability / reach-scan instrument v0.2.9"
CITATION_TEXT = (
    "If you use this instrument or the reach-scan measurement framing, please cite "
    "M.R. Nothem (2026), Reachability Labs, and the associated paper."
)
USAGE_NOTICE = (
    "Apache-2.0. Provided as a reusable measurement instrument. The shipped "
    "sources/projections are clean reference implementations, not a production "
    "extraction pipeline. For inquiries contact mnothem@reachabilitylabs.org."
)
PLOT_FOOTER = "Reachability Labs - reachscan - cite Nothem (2026)"


def provenance(extra: Dict[str, Any] | None = None) -> Dict[str, Any]:
    base = {
        "_framework": FRAMEWORK_NAME,
        "_framework_tag": FRAMEWORK_TAG,
        "_citation": CITATION_TEXT,
        "_usage_notice": USAGE_NOTICE,
        "_generated_utc": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        base.update(extra)
    return base


def write_companion_meta(path: str | Path, extra: Dict[str, Any] | None = None) -> None:
    target = Path(path)
    meta = target.with_suffix(target.suffix + ".meta.json")
    meta.write_text(json.dumps(provenance(extra), indent=2), encoding="utf-8")


def _write_csv(rows, path: Path) -> None:
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def write_result(result, outdir: str | Path) -> Path:
    """Write a ReachScanResult to outdir: summary CSV, receipts CSV, run manifest,
    each with a provenance companion. Returns the outdir path."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    summary_rows = [
        {
            "fraction": s.fraction,
            "committed_len": s.committed_len,
            "attempts": s.attempts,
            "ok_answers": s.ok_answers,
            "numeric": s.numeric,  # legacy alias of ok_answers; kept for v0.2.x compatibility
            "truncated": s.truncated,
            "cap_hits": s.cap_hits,
            "no_answer": s.no_answer,
            "rate_defined": int(s.rate_defined),
            "target_reachability": s.target_reachability,
            "target_count": s.target_count,
            "dominant_bucket": s.dominant_bucket,
            "dominant_mass": s.dominant_mass,
            "answer_field_entropy": s.answer_field_entropy,
            "wilson_target_low": s.wilson_target_low,
            "wilson_target_high": s.wilson_target_high,
            "field": json.dumps([[k, v] for k, v in s.field.items()], default=str),
        }
        for s in result.summaries
    ]
    _write_csv(summary_rows, outdir / "summary_by_depth.csv")
    write_companion_meta(outdir / "summary_by_depth.csv", {"kind": "summary_by_depth"})

    receipt_rows = [
        {
            "depth_index": r.depth_index,
            "fraction": r.fraction,
            "committed_len": r.committed_len,
            "rollout_index": r.rollout_index,
            "seed": r.seed,
            "status": r.status,
            "value": r.value,
            "bucket": r.bucket,
            "is_target": int(r.is_target),
            "hit_token_cap": int(r.hit_token_cap),
            "n_new_tokens": r.n_new_tokens,
        }
        for r in result.receipts
    ]
    _write_csv(receipt_rows, outdir / "receipts.csv")
    write_companion_meta(outdir / "receipts.csv", {"kind": "receipts"})

    manifest = provenance({"run_manifest": result.manifest})
    (outdir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return outdir


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _jsonish(value: str | None) -> Any:
    if value is None or value == "":
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _hashable(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_hashable(v) for v in value)
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    return value


def read_result(outdir: str | Path):
    """Read artifacts written by write_result() back into a ReachScanResult.

    This is intended for checkpoint/resume workflows in notebooks: completed
    per-depth checkpoints can be reloaded and combined without rerunning those
    depths. CSV typing is reconstructed for the engine's standard fields; custom
    bucket objects that were serialized through JSON fallback may round-trip as
    strings or tuples, which is sufficient for plotting and final artifact
    assembly.
    """
    from .engine import DepthSummary, ReachScanResult, RolloutReceipt

    outdir = Path(outdir)
    result = ReachScanResult()

    for row in _read_csv(outdir / "summary_by_depth.csv"):
        field_pairs = _jsonish(row.get("field")) or []
        field = {_hashable(k): int(v) for k, v in field_pairs}
        result.summaries.append(
            DepthSummary(
                fraction=float(row["fraction"]),
                committed_len=int(row["committed_len"]),
                attempts=int(row["attempts"]),
                ok_answers=int(row["ok_answers"]),
                numeric=int(row["numeric"]),
                truncated=int(row["truncated"]),
                cap_hits=int(row["cap_hits"]),
                no_answer=int(row["no_answer"]),
                target_reachability=float(row["target_reachability"]),
                rate_defined=bool(int(row["rate_defined"])),
                target_count=int(row["target_count"]),
                dominant_bucket=_jsonish(row.get("dominant_bucket")),
                dominant_mass=float(row["dominant_mass"]),
                answer_field_entropy=float(row["answer_field_entropy"]),
                wilson_target_low=float(row["wilson_target_low"]),
                wilson_target_high=float(row["wilson_target_high"]),
                field=field,
            )
        )

    for row in _read_csv(outdir / "receipts.csv"):
        result.receipts.append(
            RolloutReceipt(
                depth_index=int(row["depth_index"]),
                fraction=float(row["fraction"]),
                committed_len=int(row["committed_len"]),
                rollout_index=int(row["rollout_index"]),
                seed=int(row["seed"]),
                status=row["status"],
                value=(row["value"] if row["value"] != "" else None),
                bucket=_jsonish(row.get("bucket")),
                is_target=bool(int(row["is_target"])),
                hit_token_cap=bool(int(row["hit_token_cap"])),
                # Backward-compat: pre-0.2.8 artifacts have no token column.
                n_new_tokens=(int(row["n_new_tokens"])
                              if row.get("n_new_tokens") not in (None, "") else 0),
            )
        )

    manifest_path = outdir / "run_manifest.json"
    if manifest_path.exists():
        doc = json.loads(manifest_path.read_text(encoding="utf-8"))
        result.manifest = doc.get("run_manifest", doc)
    return result


def _part_min_depth(part) -> int:
    return min((r.depth_index for r in part.receipts), default=0)


def stitch_results(parts):
    """Combine per-depth checkpoint results into one whole-run result.

    Use this instead of hand-concatenating checkpoints: it orders parts by
    depth_index and, crucially, SUMS the cost block across them. Each per-depth
    checkpoint's manifest only covers its own depth, so naively keeping one
    checkpoint's manifest would under-report total tokens and wall-clock by the
    number of depths. Returns a ReachScanResult whose manifest drops
    `executed_depth_indices`, sets `stitched_from_checkpoints=True`, and carries
    the summed cost block (earliest start / latest end across parts).
    """
    from .engine import ReachScanResult

    ordered = sorted((p for p in parts if p is not None), key=_part_min_depth)
    merged = ReachScanResult()

    gen_by_depth: dict[str, int] = {}
    secs_by_depth: dict[str, float] = {}
    runtime = None
    starts: list[str] = []
    ends: list[str] = []
    base_manifest: dict | None = None

    for p in ordered:
        merged.summaries.extend(p.summaries)
        merged.receipts.extend(p.receipts)
        if base_manifest is None and p.manifest:
            base_manifest = dict(p.manifest)
        cost = (p.manifest or {}).get("cost") or {}
        work = cost.get("work") or {}
        env = cost.get("environment") or {}
        gen_by_depth.update(work.get("gen_tokens_by_depth") or {})
        secs_by_depth.update(env.get("wall_clock_s_by_depth") or {})
        runtime = runtime or env.get("runtime")
        if env.get("started_utc"):
            starts.append(env["started_utc"])
        if env.get("ended_utc"):
            ends.append(env["ended_utc"])

    if base_manifest is not None:
        base_manifest.pop("executed_depth_indices", None)
        base_manifest["stitched_from_checkpoints"] = True
        base_manifest["cost"] = {
            "work": {
                "gen_tokens_total": sum(gen_by_depth.values()),
                "gen_tokens_by_depth": gen_by_depth,
            },
            "environment": {
                "wall_clock_s_total": round(sum(secs_by_depth.values()), 6),
                "wall_clock_s_by_depth": secs_by_depth,
                "runtime": runtime,
                "started_utc": min(starts) if starts else None,
                "ended_utc": max(ends) if ends else None,
            },
        }
        merged.manifest = base_manifest
    return merged
