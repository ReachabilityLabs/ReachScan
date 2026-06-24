"""Projection adapter TEMPLATE — copy this directory and replace the bodies.

Three functions define your task lens:
  parse(raw_text)    -> your extracted answer (any hashable), or None if none
  is_correct(parsed) -> did it hit the correct endpoint answer? (the outcome check)
  classify(parsed)   -> one declared projection class (a string)

This template is a minimal, self-consistent lens (exact-match on an integer) so the
pack validates out of the box. Replace TARGET, the parser, and the classes with
your task's lens; keep fixtures.jsonl in sync and re-run
`reachscan projection validate`. See docs/BUILD_A_PROJECTION_PACK.md.
"""
from __future__ import annotations

import re

TARGET = 42  # TODO: your correct answer

_INT = re.compile(r"-?\d+")


def parse(raw_text: str):
    """raw model text -> extracted answer, or None."""
    if not raw_text:
        return None
    nums = _INT.findall(raw_text)
    return int(nums[-1]) if nums else None  # TODO: your real extractor


def is_correct(parsed) -> bool:
    """Outcome check: did the answer hit the correct endpoint?"""
    return isinstance(parsed, int) and parsed == TARGET  # TODO


def classify(parsed) -> str:
    """Map the parsed answer to ONE declared projection class."""
    if parsed is None:
        return "no_answer"
    if not isinstance(parsed, int):
        return "invalid"
    return "target" if parsed == TARGET else "other"  # TODO: your real classes
