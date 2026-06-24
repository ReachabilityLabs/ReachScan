"""reachscan CLI group (v0.3.0).

Subcommands for projection packs. The prediction evaluator (`prediction evaluate`)
is a later phase and is intentionally not wired here yet.

    reachscan projection validate examples/projections/floor_sum_mod8
    reachscan projection inspect  examples/projections/floor_sum_mod8
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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="reachscan", description="reachscan CLI")
    sub = ap.add_subparsers(dest="group", required=True)

    proj = sub.add_parser("projection", help="projection-pack commands")
    proj_sub = proj.add_subparsers(dest="action", required=True)
    v = proj_sub.add_parser("validate", help="validate a projection pack against its fixtures")
    v.add_argument("pack_dir")
    ins = proj_sub.add_parser("inspect", help="print a projection pack's manifest block")
    ins.add_argument("pack_dir")

    args = ap.parse_args(argv)
    if args.group == "projection":
        if args.action == "validate":
            return _projection_validate(args.pack_dir)
        if args.action == "inspect":
            return _projection_inspect(args.pack_dir)
    ap.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
