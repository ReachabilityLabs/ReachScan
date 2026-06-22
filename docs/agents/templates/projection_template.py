"""Projection template — copy, rename, fill in the three methods.

A Projection is the ONLY thing you implement to measure a new task. The engine
never changes. Contract (from reachscan.contracts.Projection):

    extract(completion_text) -> ExtractedAnswer   # pull the answer out of text
    project(answer)          -> Hashable          # assign a bucket key
    is_target(answer)        -> bool              # does it hit the target set T?

BINDING CONSISTENCY RULE (the engine enforces this and will raise ValueError if
you break it): if two answers share a project() bucket, they MUST share the same
is_target() value. Practically: make is_target a function of the bucket, not of
the raw value. The asserts at the bottom check this on your own examples before
you ever spend a GPU.

The engine only calls project()/is_target() on answers with status == "ok", so
you never have to handle value=None in those two methods.
"""
from __future__ import annotations

from typing import Hashable

# When this lives outside the repo, ensure `src` is importable, e.g.:
#   PYTHONPATH=src python docs/agents/templates/projection_template.py
from reachscan.contracts import ExtractedAnswer


class MyProjection:
    def __init__(self, target):
        # Ground truth / target set lives HERE, never as a hidden engine input.
        self.name = "my_projection"
        self.target = target

    def extract(self, completion_text: str) -> ExtractedAnswer:
        """Pull the terminal answer out of the completion text.

        Return ExtractedAnswer(ExtractedAnswer.OK, value, completion_text) when an
        answer is found (value is the canonical STRING form), else
        ExtractedAnswer(ExtractedAnswer.NO_ANSWER, None, completion_text).
        Reuse reachscan.projections._extract_numeric for boxed-number tasks, or
        write task-specific parsing here (e.g. a multiple-choice letter).
        """
        text = (completion_text or "").strip()
        if not text:
            return ExtractedAnswer(ExtractedAnswer.NO_ANSWER, None, completion_text)
        # TODO: real parsing. Placeholder: last whitespace-separated token.
        value = text.split()[-1]
        return ExtractedAnswer(ExtractedAnswer.OK, value, completion_text)

    def project(self, answer: ExtractedAnswer) -> Hashable:
        """Map an OK answer to its bucket key. Engine guarantees answer.is_ok."""
        # TODO: canonicalize into task buckets (e.g. answer.value.upper()).
        return answer.value

    def is_target(self, answer: ExtractedAnswer) -> bool:
        """Does this OK answer hit the target set T? Engine guarantees is_ok.

        Keep this a property of the project() bucket — derive it from the SAME
        canonicalization project() uses, not from raw text, or you break the rule.
        """
        return self.project(answer) == self.target


if __name__ == "__main__":
    # Minimal self-check: edit these examples for your task, then run this file.
    proj = MyProjection(target="C")

    a_target = proj.extract("...therefore the answer is C")
    a_other = proj.extract("...so the answer is A")
    a_none = proj.extract("")

    assert a_target.is_ok and proj.is_target(a_target), "target example should hit"
    assert a_other.is_ok and not proj.is_target(a_other), "non-target should miss"
    assert not a_none.is_ok, "empty completion should be NO_ANSWER"

    # Consistency rule check: any two OK answers in the same bucket must agree on
    # is_target. This is exactly what the engine enforces at scan time.
    seen: dict[Hashable, bool] = {}
    for a in (a_target, a_other):
        b = proj.project(a)
        t = proj.is_target(a)
        assert seen.get(b, t) == t, f"consistency violation in bucket {b!r}"
        seen[b] = t

    print("projection template self-check passed")
