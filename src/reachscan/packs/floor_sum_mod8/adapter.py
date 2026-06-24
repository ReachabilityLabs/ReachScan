"""Floor-sum mod-8 projection adapter.

Behavior-bearing code for the floor-sum projection pack: it is covered by the
projection pack hash, so any change here changes the pack identity. Self-contained
on purpose (no reachscan internals) so the hash pins the real parser/classifier.

Three functions, per the projection protocol:
  - parse(raw_text)      -> an integer, a verbatim string (non-integer answer), or None
  - is_correct(parsed)   -> did it hit the correct endpoint answer 532? (outcome check)
  - classify(parsed)     -> the declared projection class (residue_k / no_answer / invalid)

Note the deliberate gap between is_correct and classify: 540 is NOT correct
(is_correct False) yet lives in the target residue class residue_4. The projection
class is a residue fiber, not the exact answer.
"""
from __future__ import annotations

import re

CORRECT_ANSWER = 532
MODULUS = 8

_BOXED = re.compile(r"\\boxed\{([^}]*)\}")
_NUM = re.compile(r"-?\d+(?:\.\d+)?")
_CLEAN_INT = re.compile(r"^-?\d+$")
_ANSWER_CUE = re.compile(
    r"(?:final\s+answer|answer\s*(?:is|:|=))\s*\$?\s*(-?\d[\d,]*(?:\.\d+)?)", re.I)


def _strip_commas(s: str) -> str:
    return re.sub(r"(?<=\d),(?=\d)", "", s)


def _coerce(token: str):
    """A clean integer string -> int; any other non-empty token -> verbatim string."""
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
        span = _strip_commas(boxes[-1].strip())   # LAST box wins (self-correction)
        if _CLEAN_INT.match(span):
            return int(span)
        return span or None                        # "5/8" / "3.14" -> verbatim string
    cleaned = _strip_commas(raw_text)
    cues = list(_ANSWER_CUE.finditer(cleaned))
    if cues:
        return _coerce(cues[-1].group(1))
    nums = _NUM.findall(cleaned)
    if nums:                                        # least-reliable fallback
        return _coerce(nums[-1])
    return None


def is_correct(parsed) -> bool:
    return isinstance(parsed, int) and parsed == CORRECT_ANSWER


def classify(parsed) -> str:
    if parsed is None:
        return "no_answer"
    if isinstance(parsed, int):
        return f"residue_{parsed % MODULUS}"
    return "invalid"
