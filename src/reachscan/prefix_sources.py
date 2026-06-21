"""Prefix sources — where the committed reference trace comes from.

GeneratedPrefixSource: the model generates ONE reference trace (single-trace by
design, matching the flagship paper), freezes its ids, serves prefixes of it.
UserPrefixSource: the user supplies an already-captured trace as ids.
"""
from __future__ import annotations

from typing import Sequence

from .contracts import SamplerPolicy, TokenContinuationSource


class UserPrefixSource:
    """User supplies prompt ids and a captured reference trace (token ids)."""

    def __init__(self, prompt_ids: Sequence[int], trace_ids: Sequence[int], *, name: str = "user_trace"):
        self.name = name
        self._prompt_ids = list(prompt_ids)
        self._trace_ids = list(trace_ids)
        self.provenance = {"kind": "user_supplied"}

    def prompt_ids(self) -> list[int]:
        return list(self._prompt_ids)

    def reference_trace_ids(self) -> list[int]:
        return list(self._trace_ids)


class GeneratedPrefixSource:
    """Generate ONE reference trace from the source, freeze it, serve prefixes.

    Single-trace BY DESIGN (matches the flagship paper, which scans prefixes of a
    single primary trace). Aggregating across many traces is a different,
    future source. trace_sampler is the budget for GENERATING the trace and is
    distinct from the engine's per-depth rollout_sampler.
    """

    def __init__(
        self,
        source: TokenContinuationSource,
        prompt: str,
        *,
        trace_sampler: SamplerPolicy,
        seed: int,
        system: str | None = None,
        name: str = "generated_trace",
    ):
        self.name = name
        self._prompt_ids = list(source.encode_prompt(prompt, system=system))
        self._trace_ids = list(
            source.sample_completion(
                self._prompt_ids,
                temperature=trace_sampler.temperature,
                top_p=trace_sampler.top_p,
                top_k=trace_sampler.top_k,
                repetition_penalty=trace_sampler.repetition_penalty,
                max_new_tokens=trace_sampler.max_new_tokens,
                seed=seed,
            )
        )
        # Recorded by the engine in the run manifest (named-inputs rule).
        self.provenance = {
            "kind": "generated",
            "trace_seed": seed,
            "trace_sampler": vars(trace_sampler),
            "system": system,
        }

    def prompt_ids(self) -> list[int]:
        return list(self._prompt_ids)

    def reference_trace_ids(self) -> list[int]:
        return list(self._trace_ids)
