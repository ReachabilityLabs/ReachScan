"""reachscan contracts — the frozen interfaces the engine depends on.

This module defines the abstract prong shape the reach-scan engine plugs into.
The engine knows ONLY these contracts plus ExtractedAnswer and the seed rule.
It contains no torch, no floor-sum, no mod-8, and no tokenizer of its own.

There are three contracts and one shared value type:

  - ExtractedAnswer      : the value type that crosses all Projection methods
  - TokenContinuationSource : "given a committed prefix, yield sampled futures"
                              (the FIRST implementation of the abstract source
                              shape, for token-emitting language models)
  - PrefixSource         : "yield a committed reference trace to slice by fraction"
  - Projection           : "classify an extracted answer into a task bucket"

Substrate note: the engine depends on the abstract shape
"committed prefix -> sampled futures". TokenContinuationSource is the first and
only implementation, for token LLMs. Other substrates (agents, etc.) could be
measured by implementing the same shape; none is provided or claimed here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Hashable, Protocol, Sequence, runtime_checkable


# --------------------------------------------------------------------------
# Shared value type
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class ExtractedAnswer:
    """The terminal answer pulled from one completion, with status.

    value is the canonical STRING form when status == "ok" (string, not float,
    so no precision/format is lost before the Projection decides how to read it).
    The engine only ever calls Projection.project / Projection.is_target on
    answers with status == "ok", so projections never have to handle value=None.
    """

    status: str  # "ok" | "no_answer" | "truncated"
    value: str | None
    raw_text: str

    OK = "ok"
    NO_ANSWER = "no_answer"
    TRUNCATED = "truncated"

    @property
    def is_ok(self) -> bool:
        return self.status == "ok"


@dataclass(frozen=True)
class SamplerPolicy:
    """A decoding policy. Trace generation and per-depth rollouts each carry
    their own SamplerPolicy (they are different budgets; see contract R4).

    top_k=None means top-k filtering is DISABLED (it is never "the model's
    default"); repetition_penalty=1.0 means no penalty. Reference sources build
    their decode configuration from these fields ALONE — model-side generation
    defaults must not silently merge in (see HuggingFaceSource)."""

    temperature: float = 0.7
    top_p: float = 1.0
    top_k: int | None = None
    repetition_penalty: float = 1.0
    max_new_tokens: int = 512


# --------------------------------------------------------------------------
# Contract 1 — TokenContinuationSource
# (the first implementation of the abstract "committed prefix -> futures" shape)
# --------------------------------------------------------------------------
@runtime_checkable
class TokenContinuationSource(Protocol):
    """A token-emitting source of sampled futures from a committed prefix.

    Required surface is deliberately minimal: encode_prompt, decode,
    sample_completion. forward_logits and tokenize are NOT required (the engine
    measures completed rollouts, not vocab logits; committed prefixes are sliced
    from token ids carried by the PrefixSource, so no text tokenizer is needed).
    Keeping the surface minimal is what lets API-only models (no logit access)
    implement this contract.
    """

    name: str

    def encode_prompt(self, prompt: str, *, system: str | None = None) -> list[int]:
        """Prompt text -> token ids (instruct models apply their chat template)."""
        ...

    def decode(self, token_ids: Sequence[int]) -> str:
        """Token ids -> text (so a Projection can extract from it)."""
        ...

    def sample_completion(
        self,
        input_ids: Sequence[int],
        *,
        temperature: float,
        top_p: float,
        max_new_tokens: int,
        top_k: int | None = None,
        repetition_penalty: float = 1.0,
        stop_token_ids: Sequence[int] | None = None,
        seed: int | None = None,
        **sampler_extras,
    ) -> list[int]:
        """Sample ONE continuation from the prefix ids; return NEW tokens only.
        Distinct seeds MUST give independent draws (see engine SEED RULE).

        Seed range (binding): seeds are integers in [0, 2**64). Sources must
        accept the full range (do NOT feed them to 32-bit-only RNG seeders).

        Forward-compatibility (binding): implementations MUST accept unknown
        keyword sampler parameters (**sampler_extras). A source SHOULD raise on
        a non-default value it cannot honor rather than silently mis-measure;
        the engine records the full declared policy in the run manifest either
        way, so the declaration is always auditable."""
        ...


# --------------------------------------------------------------------------
# Contract 2 — PrefixSource
# --------------------------------------------------------------------------
@runtime_checkable
class PrefixSource(Protocol):
    """Yields the committed reference trace (as token ids) whose prefixes are
    frozen and reach-scanned, plus the prompt ids it was generated under.

    The committed prefix at fraction f is:
        prompt_ids() + reference_trace_ids()[: round(f * L)],  L = trace length.

    Carrying the trace as token IDS (not text) is what removes any need for the
    engine to tokenize. GeneratedPrefixSource is single-trace BY DESIGN (matches
    the flagship paper); multi-trace aggregation is a different, future source.
    """

    name: str

    def prompt_ids(self) -> list[int]:
        ...

    def reference_trace_ids(self) -> list[int]:
        ...


# --------------------------------------------------------------------------
# Contract 3 — Projection
# --------------------------------------------------------------------------
@runtime_checkable
class Projection(Protocol):
    """Extracts a terminal answer from completion text and classifies it.

    Consistency rule (binding): is_target must be a property of the project()
    bucket — if two answers share a project() bucket they MUST share the same
    is_target() value. The engine computes target reachability from is_target.
    Ground truth / target lives in the projection's constructor, never as a
    hidden engine input.
    """

    name: str

    def extract(self, completion_text: str) -> ExtractedAnswer:
        ...

    def project(self, answer: ExtractedAnswer) -> Hashable:
        """Map an OK answer to its bucket key. Engine guarantees answer.is_ok."""
        ...

    def is_target(self, answer: ExtractedAnswer) -> bool:
        """Does this OK answer hit target set T? Engine guarantees answer.is_ok."""
        ...
