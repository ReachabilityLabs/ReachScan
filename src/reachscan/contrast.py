"""Source-conditioned contrast — the diagnostic primitive.

Takes two reach-scan results (e.g. from correct-source and wrong-source committed
prefixes) and reports, per depth, the separation in target reachability with a
confidence interval on the difference. This is the diagnostic KERNEL.

What this gives you: the comparison, once you already have two reach-scans on the
same depth plan.

What it does NOT give you (the research, deliberately not in this repo): how to
mine candidates where the separation is large, how to generate clean labeled
correct/wrong source traces, and the production extraction behind robust answers.
You bring your own labeled sources; this computes the contrast.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .engine import ReachScanResult


@dataclass
class SeparationRow:
    fraction: float
    r_t_correct: float
    r_t_wrong: float
    separation: float      # r_t_correct - r_t_wrong
    sep_low: float         # Newcombe difference CI (from each scan's Wilson bounds)
    sep_high: float
    attempts_correct: int   # rollouts attempted
    ok_correct: int         # OK answers = the R_T denominator
    numeric_correct: int    # legacy alias of ok_correct (v0.2.x)
    attempts_wrong: int
    ok_wrong: int
    numeric_wrong: int      # legacy alias of ok_wrong (v0.2.x)


@dataclass
class SeparationCurve:
    rows: list[SeparationRow]

    def __iter__(self):
        return iter(self.rows)


def source_separation(correct: ReachScanResult, wrong: ReachScanResult) -> SeparationCurve:
    """Per-depth target-reachability separation R_T(correct) - R_T(wrong).

    The interval is Newcombe's (1998) hybrid-score interval for a difference of two
    proportions, built from each scan's Wilson interval — no new assumptions, no
    extra dependencies.

    Both scans must share the SAME ORDERED depth plan: same sequence of
    (fraction, committed_len). This is enforced — matching only rounded fractions
    would silently compare scans that differ in resolved committed length, order,
    or duplicate labels.
    """
    correct_keys = [(round(s.fraction, 6), s.committed_len) for s in correct.summaries]
    wrong_keys = [(round(s.fraction, 6), s.committed_len) for s in wrong.summaries]
    if correct_keys != wrong_keys:
        raise ValueError(
            "correct and wrong scans must share the same ordered depth plan "
            "(fraction and committed_len); run both on the same plan"
        )

    rows: list[SeparationRow] = []
    for ca, wb in zip(correct.summaries, wrong.summaries):
        if not (ca.rate_defined and wb.rate_defined):
            raise ValueError(
                f"undefined target reachability at depth {ca.fraction} "
                "(zero valid answers / extractor failure); fix yield before "
                "contrasting — a zero denominator is not zero reachability"
            )
        p1, p2 = ca.target_reachability, wb.target_reachability
        d = p1 - p2
        lo = d - math.sqrt((p1 - ca.wilson_target_low) ** 2 + (wb.wilson_target_high - p2) ** 2)
        hi = d + math.sqrt((ca.wilson_target_high - p1) ** 2 + (p2 - wb.wilson_target_low) ** 2)
        rows.append(SeparationRow(
            fraction=ca.fraction, r_t_correct=p1, r_t_wrong=p2, separation=d,
            sep_low=lo, sep_high=hi,
            attempts_correct=ca.attempts, ok_correct=ca.ok_answers, numeric_correct=ca.numeric,
            attempts_wrong=wb.attempts, ok_wrong=wb.ok_answers, numeric_wrong=wb.numeric,
        ))
    return SeparationCurve(rows)
