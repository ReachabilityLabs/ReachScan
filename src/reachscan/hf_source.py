"""HuggingFaceSource — the live TokenContinuationSource for real models.

Ported in shape from the v0.44 hf_backend. transformers/torch are imported
LAZILY inside __init__ so the package installs and the mock path runs with zero
heavy dependencies; you only need torch/transformers if you actually construct
this class. This is the "real model" appliance that plugs into the same engine
as the mock.

NOTE: this file is not exercised in the CI test suite (no GPU/weights in CI).
It is the live path you run on a real model (e.g. Qwen2.5-Math-7B-Instruct).
"""
from __future__ import annotations

from typing import Sequence


class HuggingFaceSource:
    name: str

    def __init__(
        self,
        model_id: str,
        *,
        device: str | None = None,
        torch_dtype: str = "auto",
        chat_template: bool = True,
        revision: str | None = None,
    ):
        # Lazy imports: keep the package importable without torch installed.
        import torch  # noqa: F401
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.name = f"hf:{model_id}" + (f"@{revision}" if revision else "")
        self.revision = revision
        self.model_id = model_id
        self.chat_template = chat_template
        self._tok = AutoTokenizer.from_pretrained(model_id, revision=revision)
        self._model = AutoModelForCausalLM.from_pretrained(
            model_id, revision=revision, torch_dtype=torch_dtype, device_map=device or "auto"
        )
        self._model.eval()
        self._torch = torch
        self.vocab_size = self._tok.vocab_size

    def encode_prompt(self, prompt: str, *, system: str | None = None) -> list[int]:
        if self.chat_template and self._tok.chat_template:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            ids = self._tok.apply_chat_template(
                messages, add_generation_prompt=True, tokenize=True
            )
            return list(ids)
        return list(self._tok(prompt, add_special_tokens=True)["input_ids"])

    def decode(self, token_ids: Sequence[int]) -> str:
        return self._tok.decode(list(token_ids), skip_special_tokens=True)

    # Receipt-visible declaration of how this adapter builds its decode policy.
    sampler_semantics = (
        "explicit-generation-config: the decode policy is built from the declared "
        "SamplerPolicy fields alone; the model's own generation_config defaults "
        "(top_k, penalties, etc.) are NOT merged. top_k=None disables top-k."
    )

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
        torch = self._torch
        from transformers import GenerationConfig

        if seed is not None:
            torch.manual_seed(seed)
        prompt_len = len(input_ids)
        inp = torch.tensor([list(input_ids)], device=self._model.device)
        attn = torch.ones_like(inp)
        eos = list(stop_token_ids) if stop_token_ids else self._tok.eos_token_id
        gen_cfg = GenerationConfig(
            do_sample=temperature > 0,
            temperature=max(temperature, 1e-5),
            top_p=top_p,
            top_k=int(top_k) if top_k is not None else 0,  # 0 disables top-k
            repetition_penalty=float(repetition_penalty),
            max_new_tokens=max_new_tokens,
            eos_token_id=eos,
            pad_token_id=self._tok.pad_token_id or self._tok.eos_token_id,
        )
        with torch.no_grad():
            out = self._model.generate(inp, attention_mask=attn, generation_config=gen_cfg)
        new_ids = out[0].tolist()[prompt_len:]
        return new_ids
