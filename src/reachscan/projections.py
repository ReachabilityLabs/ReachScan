"""Reference projections. Each is a clean reference implementation — NOT the
full production extractor. Ground truth / target lives in the constructor, never
as a hidden engine input. Each satisfies the binding consistency rule: is_target
is a property of the project() bucket.

Extraction policy (v0.2 reference extractor — documented because it is brittle by
design, not by accident):
  1. Prefer the LAST \\boxed{...} (handles a model that self-corrects).
  2. Strip thousands-separator commas between digits (1,234 -> 1234).
  3. A boxed answer that is not a single clean number is returned verbatim
     (e.g. "5/8"), so it becomes its own bucket rather than being mis-read.
  4. With no box, prefer the number after an explicit answer cue
     ("answer is", "final answer", "= ..."), else fall back to the last number.
Non-integer answers (decimals, fractions, expressions) are bucketed explicitly
as non-integers rather than silently coerced. For answer formats this does not
cover, supply your own Projection.extract — that is the contract's whole point.
"""
from __future__ import annotations

import re
from typing import Hashable

from .contracts import ExtractedAnswer, Projection

_BOXED = re.compile(r"\\boxed\{([^}]*)\}")
_NUM = re.compile(r"-?\d+(?:\.\d+)?")
_CLEAN_INT = re.compile(r"^-?\d+$")
_ANSWER_CUE = re.compile(
    r"(?:final\s+answer|answer\s*(?:is|:|=))\s*\$?\s*(-?\d[\d,]*(?:\.\d+)?)", re.I
)


def _strip_commas(s: str) -> str:
    return re.sub(r"(?<=\d),(?=\d)", "", s)


def _extract_numeric(text: str) -> ExtractedAnswer:
    """Boxed-first, comma-safe, self-correction-safe reference extractor."""
    if not text:
        return ExtractedAnswer(ExtractedAnswer.NO_ANSWER, None, text)

    boxes = _BOXED.findall(text)
    if boxes:
        span = _strip_commas(boxes[-1].strip())  # LAST box wins
        if _CLEAN_INT.match(span):
            return ExtractedAnswer(ExtractedAnswer.OK, span, text)
        nums = _NUM.findall(span)
        if len(nums) == 1:  # a single clean number in the box (incl. decimal)
            return ExtractedAnswer(ExtractedAnswer.OK, nums[0], text)
        if span:            # fraction / expression / multi-number -> verbatim bucket
            return ExtractedAnswer(ExtractedAnswer.OK, span, text)
        return ExtractedAnswer(ExtractedAnswer.NO_ANSWER, None, text)

    cleaned = _strip_commas(text)
    cues = list(_ANSWER_CUE.finditer(cleaned))
    if cues:
        return ExtractedAnswer(ExtractedAnswer.OK, cues[-1].group(1), text)
    nums = _NUM.findall(cleaned)
    if nums:  # least-reliable fallback (no box, no cue)
        return ExtractedAnswer(ExtractedAnswer.OK, nums[-1], text)
    return ExtractedAnswer(ExtractedAnswer.NO_ANSWER, None, text)


def _as_int(value: str | None):
    """Return an int iff value is a clean integer string, else None.
    Non-integers (3.14, 5/8) return None and get an explicit non-integer bucket,
    never a silent coercion."""
    if value is None:
        return None
    if _CLEAN_INT.match(value.strip()):
        return int(value)
    return None


def _canonical(value: str | int | None) -> str | None:
    """Canonical string form: integers normalize (e.g. '0532' -> '532'),
    everything else is the stripped verbatim string ('5/8' stays '5/8')."""
    if value is None:
        return None
    txt = str(value).strip()
    iv = _as_int(txt)
    return str(iv) if iv is not None else txt


class ExactMatch:
    """Bucket = the canonical answer; target = equals ground_truth.

    Accepts integer AND non-integer ground truths ('5/8', 'x+1'); both sides are
    canonicalized the same way, so the binding consistency rule holds: is_target
    is a property of the project() bucket."""

    def __init__(self, ground_truth: str | int):
        self.name = "exact_match"
        gt = _canonical(ground_truth)
        if not gt:
            raise ValueError("ExactMatch requires a non-empty ground truth")
        self._gt = gt

    def extract(self, completion_text: str) -> ExtractedAnswer:
        return _extract_numeric(completion_text)

    def project(self, answer: ExtractedAnswer) -> Hashable:
        return _canonical(answer.value)

    def is_target(self, answer: ExtractedAnswer) -> bool:
        return _canonical(answer.value) == self._gt


class ModuloProjection:
    """Bucket = value mod k; target = (bucket == target_residue) if given.

    The floor-sum flagship is ModuloProjection(8, target_residue=4), i.e.
    532 % 8 == 4. The flagship is a CONFIG of this general projection, not a
    special engine path. Non-integer answers bucket as non-integers.
    """

    def __init__(self, k: int, target_residue: int | None = None):
        k = int(k)
        if k <= 0:
            raise ValueError(f"ModuloProjection modulus must be > 0; got {k}")
        self.name = f"mod_{k}"
        self.k = k
        # Normalize so an out-of-range residue (e.g. 12 for k=8) still matches.
        self.target_residue = target_residue % k if target_residue is not None else None

    def extract(self, completion_text: str) -> ExtractedAnswer:
        return _extract_numeric(completion_text)

    def project(self, answer: ExtractedAnswer) -> Hashable:
        iv = _as_int(answer.value)
        return iv % self.k if iv is not None else "non_int"

    def is_target(self, answer: ExtractedAnswer) -> bool:
        if self.target_residue is None:
            return False
        iv = _as_int(answer.value)
        return iv is not None and (iv % self.k) == self.target_residue


class TargetFiber:
    """Explicit target-fiber framing: target = answers in the residue class of a
    known correct answer under a modulus. Mirrors the paper's target fiber
    Y ≡ 4 (mod 8) for the correct answer 532."""

    def __init__(self, modulus: int, correct_answer: int):
        modulus = int(modulus)
        if modulus <= 0:
            raise ValueError(f"TargetFiber modulus must be > 0; got {modulus}")
        self.name = f"target_fiber_mod_{modulus}"
        self.k = modulus
        self._target_residue = int(correct_answer) % modulus

    def extract(self, completion_text: str) -> ExtractedAnswer:
        return _extract_numeric(completion_text)

    def project(self, answer: ExtractedAnswer) -> Hashable:
        iv = _as_int(answer.value)
        return iv % self.k if iv is not None else "non_int"

    def is_target(self, answer: ExtractedAnswer) -> bool:
        iv = _as_int(answer.value)
        return iv is not None and (iv % self.k) == self._target_residue
