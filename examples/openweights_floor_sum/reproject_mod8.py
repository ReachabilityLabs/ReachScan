"""Recompute the mod-8 family view from reach-scan receipts.

Reads ``receipts.csv`` and recomputes target reachability under
``ModuloProjection(8, target_residue=4)`` from the same extracted answers — no
model rerun. For v0.3.3 Llama runs, ``floor_sum_mod8`` is already the primary
projection pack, so this script is a consistency/helper view. It also supports
older ExactMatch-primary artifacts.

Usage::

    python reproject_mod8.py [path/to/receipts.csv]
"""
from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

from reachscan import ExtractedAnswer, ModuloProjection


def reproject(receipts_csv: str | Path, modulus: int = 8, target_residue: int = 4):
    """Per-depth mod-``modulus`` reachability from a run's extracted answers.

    Uses the engine's own ``ModuloProjection`` so the buckets match exactly what a
    native mod-k run would have produced.
    """
    proj = ModuloProjection(modulus, target_residue=target_residue)
    by_depth: dict[tuple[int, float], list[ExtractedAnswer]] = {}
    with open(receipts_csv, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["status"] != ExtractedAnswer.OK:
                continue
            key = (int(row["depth_index"]), float(row["fraction"]))
            by_depth.setdefault(key, []).append(
                ExtractedAnswer(ExtractedAnswer.OK, row["value"], "")
            )

    out = []
    for (_, fraction), answers in sorted(by_depth.items()):
        field = Counter(proj.project(a) for a in answers)
        n = len(answers)
        target = sum(1 for a in answers if proj.is_target(a))
        dom_bucket, dom_n = (
            max(field.items(), key=lambda kv: kv[1]) if field else (None, 0)
        )
        out.append({
            "fraction": fraction,
            "ok_answers": n,
            "target_count": target,
            "R_T_mod": target / n if n else 0.0,
            "dominant_residue": dom_bucket,
            "dominant_mass": dom_n / n if n else 0.0,
        })
    return out


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "artifacts/receipts.csv"
    if not Path(path).exists():
        raise SystemExit(f"receipts not found: {path} (run the scan first)")
    rows = reproject(path)
    print(f"{'depth':>6} {'ok':>5} {'tgt':>5} {'R_T(mod8)':>10} "
          f"{'dom_res':>8} {'dom_mass':>8}")
    for r in rows:
        print(f"{r['fraction']:>6.2f} {r['ok_answers']:>5} {r['target_count']:>5} "
              f"{r['R_T_mod']:>10.3f} {str(r['dominant_residue']):>8} "
              f"{r['dominant_mass']:>8.3f}")


if __name__ == "__main__":
    main()
