"""Floor-sum exact-answer adapter (companion / sanity lens).

A deliberately strict lens: the target class is *exactly* 532, so target
reachability under this pack is exact-answer reachability — a sanity check that
runs alongside the morphology lens (floor_sum_mod8), not the main claim-bearing
lens. There is only one non-target class ("other"), so this pack carries no
prediction block: wrong-answer morphology needs the residue families of
floor_sum_mod8.

  parse(raw_text)    -> an integer, a verbatim string (non-integer answer), or None
  is_correct(parsed) -> parsed == 532
  classify(parsed)   -> "target" (==532) / "other" (other int) / "no_answer" / "invalid"
"""
from __future__ import annotations

import re

CORRECT_ANSWER = 532

_BOXED = re.compile(r"\\boxed\{([^}]*)\}")
_NUM = re.compile(r"-?\d+(?:\.\d+)?")
_CLEAN_INT = re.compile(r"^-?\d+$")
_ANSWER_CUE = re.compile(
    r"(?:final\s+answer|answer\s*(?:is|:|=))\s*\$?\s*(-?\d[\d,]*(?:\.\d+)?)", re.I)


def _strip_commas(s: str) -> str:
    return re.sub(r"(?<=\d),(?=\d)", "", s)


def _coerce(token: str):
    token = token.strip()
    if not token:
        return None
    if _CLEAN_INT.match(token):
        return int(token)
    return token


def parse(raw_text: str):
    """Boxed-first, comma-safe reference parser. Returns int, str, or None."""
    if not raw_text:
        return None
    boxes = _BOXED.findall(raw_text)
    if boxes:
        span = _strip_commas(boxes[-1].strip())
        if _CLEAN_INT.match(span):
            return int(span)
        return span or None
    cleaned = _strip_commas(raw_text)
    cues = list(_ANSWER_CUE.finditer(cleaned))
    if cues:
        return _coerce(cues[-1].group(1))
    nums = _NUM.findall(cleaned)
    if nums:
        return _coerce(nums[-1])
    return None


def is_correct(parsed) -> bool:
    return isinstance(parsed, int) and parsed == CORRECT_ANSWER


def classify(parsed) -> str:
    if parsed is None:
        return "no_answer"
    if not isinstance(parsed, int):
        return "invalid"
    return "target" if parsed == CORRECT_ANSWER else "other"
