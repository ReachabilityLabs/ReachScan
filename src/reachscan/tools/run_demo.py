"""reachscan-demo: run a reach-scan and write artifacts.

Default uses the zero-dependency mock source (proves the pipeline, NOT a real
result). Pass --hf MODEL_ID to run on a real HuggingFace model (requires the
[hf] extra). The floor-sum projection is ModuloProjection(8, target_residue=4).
"""
from __future__ import annotations

import argparse
from pathlib import Path

from reachscan import (
    DepthSpec, GeneratedPrefixSource, ModuloProjection, MockSource, SamplerPolicy,
)
from reachscan.engine import reach_scan
from reachscan.metadata import write_result

FLOORSUM_PROMPT = ("Please reason step by step, and put your final answer within "
                   "\\boxed{}. Problem: Compute the sum of floor((3n+7)/5) for "
                   "n = 1 through n = 40.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Run a reach-scan demo.")
    ap.add_argument("--out", default="demo_run")
    ap.add_argument("--hf", default=None, help="HuggingFace model id (needs [hf] extra). Omit to use the mock.")
    ap.add_argument("--M", type=int, default=128, help="rollouts per depth")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    if args.hf:
        from reachscan.hf_source import HuggingFaceSource
        source = HuggingFaceSource(args.hf)
        trace_budget, rollout_budget = 2048, 512
    else:
        source = MockSource(basin_value=56)
        trace_budget, rollout_budget = 160, 16
        print("[note] using MOCK source — proves the pipeline runs; NOT a real result. "
              "Use --hf MODEL_ID for a real model.")

    prefix_source = GeneratedPrefixSource(
        source, FLOORSUM_PROMPT, trace_sampler=SamplerPolicy(max_new_tokens=trace_budget), seed=args.seed
    )
    projection = ModuloProjection(8, target_residue=4)  # 532 % 8 == 4
    plan = [DepthSpec(0.0, args.M), DepthSpec(0.25, args.M), DepthSpec(0.5, args.M),
            DepthSpec(0.75, args.M), DepthSpec(1.0, args.M)]

    result = reach_scan(source=source, prefix_source=prefix_source, projection=projection,
                        plan=plan, rollout_sampler=SamplerPolicy(max_new_tokens=rollout_budget),
                        base_seed=args.seed)
    out = write_result(result, Path(args.out))

    print(f"\n{'depth':>6} {'M':>5} {'numeric':>7} {'R_T':>6} {'dom':>5} {'dom_mass':>8} {'entropy':>7}")
    for s in result.summaries:
        print(f"{s.fraction:>6.2f} {s.attempts:>5} {s.numeric:>7} {s.target_reachability:>6.3f} "
              f"{str(s.dominant_bucket):>5} {s.dominant_mass:>8.3f} {s.answer_field_entropy:>7.3f}")
    print(f"\n[done] artifacts written to {out}/")


if __name__ == "__main__":
    main()
