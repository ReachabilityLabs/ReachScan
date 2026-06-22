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

FRAMEWORK_NAME = "Reachability Labs reachscan v0.2.3"
FRAMEWORK_TAG = "Nothem Reachability / reach-scan instrument v0.2.3"
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
            "target_reachability": s.target_reachability,
            "target_count": s.target_count,
            "dominant_bucket": s.dominant_bucket,
            "dominant_mass": s.dominant_mass,
            "answer_field_entropy": s.answer_field_entropy,
            "wilson_target_low": s.wilson_target_low,
            "wilson_target_high": s.wilson_target_high,
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
        }
        for r in result.receipts
    ]
    _write_csv(receipt_rows, outdir / "receipts.csv")
    write_companion_meta(outdir / "receipts.csv", {"kind": "receipts"})

    manifest = provenance({"run_manifest": result.manifest})
    (outdir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return outdir
