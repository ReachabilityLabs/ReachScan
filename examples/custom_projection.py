"""Worked example: writing a Projection for YOUR task.

The engine measures any task you can express as a Projection — three methods:

    extract(text)      -> ExtractedAnswer   (pull the answer out of completion text)
    project(answer)    -> Hashable          (which bucket of the future field)
    is_target(answer)  -> bool              (does this answer hit the target set?)

The shipped ExactMatch / ModuloProjection are numeric. Nothing about the engine is.
Below is a NON-arithmetic projection for a multiple-choice task, to show the
instrument is not floor-sum-specific. Copy this file, change three methods, and
you are measuring reach-to-target on your own task.

Run it GPU-free to see it classify example completions:

    python examples/custom_projection.py
"""
from __future__ import annotations

import re
from typing import Hashable

from reachscan.contracts import ExtractedAnswer, Projection

_CHOICE = re.compile(r"\b([A-D])\b")
_BOXED = re.compile(r"\\boxed\{\s*([A-D])\s*\}")


class ChoiceProjection:
    """Multiple-choice task. Bucket = the chosen letter; target = correct letter.

    Satisfies the binding consistency rule: is_target is a function of the
    project() bucket (same letter -> same target verdict). Ground truth lives in
    the constructor, never as a hidden engine input.
    """

    def __init__(self, correct_choice: str):
        self.name = "multiple_choice_ABCD"
        self._gt = correct_choice.strip().upper()

    def extract(self, completion_text: str) -> ExtractedAnswer:
        if not completion_text:
            return ExtractedAnswer(ExtractedAnswer.NO_ANSWER, None, completion_text)
        m = _BOXED.search(completion_text)
        if m:
            return ExtractedAnswer(ExtractedAnswer.OK, m.group(1).upper(), completion_text)
        # else: last standalone A-D letter the model emits
        hits = _CHOICE.findall(completion_text.upper())
        if hits:
            return ExtractedAnswer(ExtractedAnswer.OK, hits[-1], completion_text)
        return ExtractedAnswer(ExtractedAnswer.NO_ANSWER, None, completion_text)

    def project(self, answer: ExtractedAnswer) -> Hashable:
        return answer.value  # the chosen letter is the bucket

    def is_target(self, answer: ExtractedAnswer) -> bool:
        return answer.value == self._gt


def _demo() -> None:
    proj = ChoiceProjection(correct_choice="C")
    examples = [
        ("...therefore the answer is \\boxed{C}.", "ok/target"),
        ("I think it's B, on reflection A.",        "ok/non-target (last letter A)"),
        ("The reasoning is long but inconclusive.", "no_answer"),
    ]
    # confirm it conforms to the Projection protocol the engine depends on
    assert isinstance(proj, Projection), "must satisfy the Projection contract"
    for text, label in examples:
        a = proj.extract(text)
        if a.is_ok:
            print(f"[{label:28}] value={a.value!r}  bucket={proj.project(a)!r}  target={proj.is_target(a)}")
        else:
            print(f"[{label:28}] status={a.status}")


if __name__ == "__main__":
    _demo()
