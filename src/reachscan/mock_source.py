"""MockSource — a deterministic, zero-dependency TokenContinuationSource.

HONESTY NOTE: this is a TEST FIXTURE, not a realistic model. Its job is to prove
the engine runs end to end with no GPU and to exercise the measurement logic with
a field whose shape shifts as the committed prefix grows (so tests can verify the
engine detects basin/foreclosure structure). It does NOT demonstrate a meaningful
scientific result; a real result needs a real model (HuggingFaceSource).

Design: completions are short integer strings. The distribution over which
integer is produced depends on (a) how deep into the reference trace the
committed prefix reaches and (b) the per-rollout seed, so:
  - distinct seeds give distinct draws (no determinism collapse),
  - as commitment deepens, target-family mass collapses and a fixed "basin"
    integer takes over (a toy analogue of foreclosure), and
  - the prompt-only state (f=0) is genuinely un-drifted.
Depth is inferred as (len(input_ids) - prompt_len) / drift_span, where
prompt_len is captured at the first encode_prompt call; if the prompt was never
encoded through this source (e.g. UserPrefixSource flows), absolute length is
used as a fallback. Fixture semantics, documented, nothing more.

The mock RESPECTS max_new_tokens (emissions are truncated to the budget), so
cap-hit accounting is exercisable without a real model. It accepts and ignores
decoding knobs it has no analogue for (top_k, repetition_penalty,
**sampler_extras) — permitted for a labeled fixture.
"""
from __future__ import annotations

import random
from typing import Sequence


class MockSource:
    name = "mock_source_v2"

    # Toy answer pool: a "target" residue family (mod 8 == 4, incl. 532) and a
    # "basin" residue family (mod 8 == 0). Values are arbitrary.
    _TARGET_FAMILY = [532, 4, 12, 20]   # mod 8 == 4
    _BASIN_FAMILY = [56, 112, 72, 88]   # mod 8 == 0

    def __init__(self, *, basin_value: int = 56, drift_strength: float = 1.0,
                 drift_span: int = 120):
        self.basin_value = basin_value
        self.drift_strength = drift_strength
        self.drift_span = drift_span
        self._prompt_len: int | None = None

    def encode_prompt(self, prompt: str, *, system: str | None = None) -> list[int]:
        ids = [min(ord(c), 255) for c in prompt][:256] or [1]
        if self._prompt_len is None:  # capture the prompt baseline once
            self._prompt_len = len(ids)
        return ids

    def decode(self, token_ids: Sequence[int]) -> str:
        return "".join(chr(t) for t in token_ids if 0 <= t < 0x110000)

    def _depth(self, committed_len: int) -> float:
        if self._prompt_len is not None:
            over = max(0, committed_len - self._prompt_len)
        else:  # fallback: absolute-length proxy (UserPrefixSource flows)
            over = committed_len
        return min(1.0, over / max(1, self.drift_span)) * self.drift_strength

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
        rng = random.Random(seed)
        d = min(1.0, self._depth(len(input_ids)))

        pool, weights = [], []
        for v in self._TARGET_FAMILY:
            pool.append(v)
            weights.append(max(0.05, 2.0 * (1.0 - 0.85 * d)))  # target mass collapses
        for v in self._BASIN_FAMILY:
            pool.append(v)
            weights.append(1.0 + 2.0 * d)
        # The configured basin (wherever it lives in the pool) takes over with
        # depth — so basin_value=532 models a CORRECT-source arm (the field
        # collapses INTO the target) and basin_value=56 a WRONG-source arm.
        for i, v in enumerate(pool):
            if v == self.basin_value:
                weights[i] += 7.0 * d

        choice = rng.choices(pool, weights=weights, k=1)[0]
        # Pad with "reasoning" filler sized to the budget so a generated
        # reference TRACE is long enough to exercise depth (a real model's
        # trace is long; an instant answer would make every depth shallow).
        filler = "." * max(0, min(int(max_new_tokens) - 12, 140))
        text = f"{filler}\\boxed{{{choice}}}"
        ids = [min(ord(c), 255) for c in text]
        return ids[: max(1, int(max_new_tokens))]
