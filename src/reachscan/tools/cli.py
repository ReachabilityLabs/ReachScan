"""reachscan CLI group (v0.3.x).

Subcommands for projection packs and prediction verdicts.

    reachscan projection validate examples/projections/floor_sum_mod8
    reachscan projection inspect  examples/projections/floor_sum_mod8
    reachscan prediction evaluate <run_dir> --projection examples/projections/floor_sum_mod8
"""
from __future__ import annotations

import argparse
import sys


def _projection_validate(pack_dir: str) -> int:
    from reachscan.projection_pack import load_projection_pack, validate_fixtures

    pack = load_projection_pack(pack_dir)
    errors = validate_fixtures(pack)
    print(f"projection_id      : {pack.projection_id} v{pack.projection_version}")
    print(f"projection_pack_hash: {pack.pack_hash.value}")
    print(f"target_class        : {pack.target_class}")
    print(f"declared_classes    : {', '.join(pack.declared_classes)}")
    print(f"claim_level         : {pack.claim_level}")
    if errors:
        print(f"\nFIXTURES FAILED ({len(errors)}):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print("\nfixtures: PASS")
    return 0


def _projection_inspect(pack_dir: str) -> int:
    import json

    from reachscan.projection_pack import load_projection_pack

    pack = load_projection_pack(pack_dir)
    print(json.dumps(pack.pack_meta, indent=2))
    return 0


def _prediction_evaluate(pack_dir: str, run_dir: str, out: str | None) -> int:
    from reachscan.metadata import read_result
    from reachscan.prediction import (
        evaluate_run,
        update_manifest_with_verdict,
        write_prediction_verdict,
    )
    from reachscan.projection_pack import load_projection_pack

    pack = load_projection_pack(pack_dir)
    if not pack.prediction:
        print(f"[prediction] pack {pack.projection_id} has no prediction block",
              file=sys.stderr)
        return 2
    result = read_result(run_dir)
    if not result.receipts:
        print(f"[prediction] no receipts in {run_dir}", file=sys.stderr)
        return 2

    # Projection lock: the run must have used THIS pack (no post-hoc pack swap).
    run_hash = (result.manifest.get("projection_pack") or {}).get("projection_pack_hash")
    if run_hash != pack.pack_hash.value:
        print(f"[prediction] projection-pack mismatch: run used {run_hash!r}, "
              f"pack is {pack.pack_hash.value!r}", file=sys.stderr)
        return 2

    verdict = evaluate_run(pack, result)
    out_dir = out or run_dir
    path = write_prediction_verdict(verdict, out_dir, prediction=pack.prediction,
                                    pack=pack, run_meta={
                                        "source": result.manifest.get("source"),
                                        "package_version": result.manifest.get("package_version"),
                                        "engine_schema": result.manifest.get("engine_schema"),
                                        "source_arm": result.manifest.get("source_arm"),
                                    })
    update_manifest_with_verdict(out_dir, verdict, prediction=pack.prediction)

    print(f"projection : {pack.projection_id}  {pack.pack_hash.value}")
    print("-" * 60)
    for t in verdict.tests:
        stat = "" if t.statistic is None else f"  stat={t.statistic:.3f}"
        print(f"  [{t.outcome:>12}] {t.test_id} ({t.test_type}){stat}")
    print("-" * 60)
    print(f"VERDICT    : {verdict.outcome.upper()}")
    print(f"written to : {path}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="reachscan", description="reachscan CLI")
    sub = ap.add_subparsers(dest="group", required=True)

    proj = sub.add_parser("projection", help="projection-pack commands")
    proj_sub = proj.add_subparsers(dest="action", required=True)
    v = proj_sub.add_parser("validate", help="validate a projection pack against its fixtures")
    v.add_argument("pack_dir")
    ins = proj_sub.add_parser("inspect", help="print a projection pack's manifest block")
    ins.add_argument("pack_dir")

    pred = sub.add_parser("prediction", help="prediction-contract commands")
    pred_sub = pred.add_subparsers(dest="action", required=True)
    ev = pred_sub.add_parser("evaluate", help="evaluate a pack's prediction against a run")
    ev.add_argument("run_dir")
    ev.add_argument("--projection", required=True, help="projection pack directory")
    ev.add_argument("--out", default=None, help="where to write the verdict (default: run_dir)")

    args = ap.parse_args(argv)
    if args.group == "projection":
        if args.action == "validate":
            return _projection_validate(args.pack_dir)
        if args.action == "inspect":
            return _projection_inspect(args.pack_dir)
    if args.group == "prediction" and args.action == "evaluate":
        return _prediction_evaluate(args.projection, args.run_dir, args.out)
    ap.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
