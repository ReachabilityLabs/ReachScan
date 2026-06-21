"""Diagnostic use: source-conditioned contrast (illustrative, GPU-free).

In real use you supply prefixes drawn from correct-source and wrong-source traces
— your own labeled data. Here we stand in two mock sources with different basins to
show the API and a non-zero separation curve. THE MOCK IS NOT A RESULT.

Finding candidates with large separation and generating clean labeled sources is
the research and is not included in this repo.
"""
from reachscan import (
    reach_scan, MockSource, GeneratedPrefixSource, ExactMatch,
    SamplerPolicy, uniform_plan, source_separation,
)


def scan(basin: int):
    src = MockSource(basin_value=basin)
    pre = GeneratedPrefixSource(
        src, "compute the answer", trace_sampler=SamplerPolicy(max_new_tokens=40), seed=0
    )
    return reach_scan(
        source=src, prefix_source=pre, projection=ExactMatch(532),
        plan=uniform_plan([0.0, 0.5, 0.9, 1.0], 128),
        rollout_sampler=SamplerPolicy(max_new_tokens=16), base_seed=0,
    )


if __name__ == "__main__":
    correct = scan(532)   # a source that stays viable toward the correct answer
    wrong = scan(56)      # a source that forecloses toward a wrong basin
    print(f"{'depth':>6} {'R_T(corr)':>10} {'R_T(wrong)':>11} {'separation':>11}  95% CI")
    for r in source_separation(correct, wrong):
        print(f"{r.fraction:>6.2f} {r.r_t_correct:>10.3f} {r.r_t_wrong:>11.3f} "
              f"{r.separation:>+11.3f}  [{r.sep_low:+.3f}, {r.sep_high:+.3f}]")
