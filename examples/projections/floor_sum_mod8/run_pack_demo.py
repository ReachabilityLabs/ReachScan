"""Run a reach-scan driven by the floor_sum_mod8 projection pack (mock source).

    python examples/projections/floor_sum_mod8/run_pack_demo.py --out /tmp/pack_run

Demonstrates Phase 3 binding: the pack validates against its fixtures, then drives
a scan whose run_manifest.json carries the `projection_pack` block and whose
receipts carry `projection_class` + projection identity. The source is a MockSource,
so this is a PIPELINE demonstration, not a scientific result.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from reachscan import (
    DepthSpec, GeneratedPrefixSource, MockSource, SamplerPolicy,
    load_projection_pack, reach_scan, validate_fixtures,
)
from reachscan.metadata import write_result

PROMPT = ("Please reason step by step, and put your final answer within \\boxed{}. "
          "Problem: Compute the sum of floor((3n+7)/5) for n = 1 through n = 40.")
HERE = Path(__file__).resolve().parent


def main() -> None:
    ap = argparse.ArgumentParser(description="Pack-driven mock reach-scan.")
    ap.add_argument("--out", default="pack_run")
    ap.add_argument("--M", type=int, default=32)
    args = ap.parse_args()

    pack = load_projection_pack(HERE)
    errors = validate_fixtures(pack)
    if errors:
        raise SystemExit(f"pack fixtures failed; refusing to run: {errors}")
    print(f"[pack] {pack.projection_id} v{pack.projection_version}  {pack.pack_hash.value}")

    src = MockSource(basin_value=56)
    prefix = GeneratedPrefixSource(src, PROMPT,
                                   trace_sampler=SamplerPolicy(max_new_tokens=160), seed=0)
    result = reach_scan(
        source=src, prefix_source=prefix, projection=pack,
        plan=[DepthSpec(f, args.M) for f in (0.0, 0.5, 0.9, 1.0)],
        rollout_sampler=SamplerPolicy(max_new_tokens=16), base_seed=0,
        source_arm="natural_trace")
    out = write_result(result, Path(args.out))

    print("[manifest] projection block:")
    print(json.dumps(result.manifest["projection_pack"], indent=2))
    print("\n[receipts] class mass at f=0.9 (mock — not a result):")
    deep = [r for r in result.receipts if r.fraction == 0.9 and r.status == "ok"]
    counts: dict[str, int] = {}
    for r in deep:
        counts[r.projection_class] = counts.get(r.projection_class, 0) + 1
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {k:>10}: {v}")
    print(f"\n[done] artifacts written to {out}/")


if __name__ == "__main__":
    main()
