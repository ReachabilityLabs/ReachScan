"""Notebook run-contract helpers.

The quickstart notebook uses this module to make the model choice explicit
before any expensive or interpretable run starts. The module is intentionally
lightweight: importing it must not import torch or transformers.
"""
from __future__ import annotations

import json
import os
import platform
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contracts import SamplerPolicy
from .engine import DepthSpec
from .projections import ExactMatch

FLOORSUM_PROMPT = (
    "Please reason step by step, and put your final answer within \\boxed{}. "
    "Problem: Compute the sum of floor((3n+7)/5) for n = 1 through n = 40."
)
FLOORSUM_ANSWER = 532

TRACE_SAMPLER = SamplerPolicy(
    temperature=0.7,
    top_p=1.0,
    top_k=None,
    repetition_penalty=1.0,
    max_new_tokens=2048,
)
ROLLOUT_SAMPLER = SamplerPolicy(
    temperature=0.7,
    top_p=1.0,
    top_k=None,
    repetition_penalty=1.0,
    max_new_tokens=512,
)
BASE_SEED = 0

PREDECLARED_PLAN = (
    (0.0, 128),
    (0.25, 64),
    (0.5, 64),
    (0.75, 128),
    (0.9, 128),
    (1.0, 128),
)
SMOKE_PLAN = ((0.0, 16), (0.5, 16), (1.0, 16))


@dataclass(frozen=True)
class ModelPreset:
    """A named model choice and its claim boundary."""

    model_id: str
    role: str
    gated: bool
    claim_ceiling: tuple[str, ...]
    requires_revision: bool = True


@dataclass(frozen=True)
class RigorPreset:
    """A named rollout plan and artifact discipline."""

    label: str
    plan: tuple[tuple[float, int], ...]
    checkpointed: bool


MODEL_PRESETS: dict[str, ModelPreset] = {
    "smoke": ModelPreset(
        "Qwen/Qwen2.5-1.5B-Instruct",
        "smoke / pipeline check",
        False,
        (
            "May verify Hugging Face loading, tokenizer behavior, generation, "
            "and artifact shape.",
            "May not support a scientific claim, cross-model replication, "
            "foreclosure, or generality.",
            "Treat any observed morphology as illustrative until rerun under "
            "a declared real-run tier.",
        ),
        requires_revision=False,
    ),
    "paper_family": ModelPreset(
        "Qwen/Qwen2.5-Math-7B-Instruct",
        "paper-family reproducibility",
        True,
        (
            "May support a single-model reachability trend on the paper-family "
            "Qwen math model.",
            "May not support cross-architecture generality because it is still "
            "inside the Qwen family.",
        ),
    ),
    "cross_family": ModelPreset(
        "meta-llama/Llama-3.1-8B-Instruct",
        "cross-family check (Llama)",
        True,
        (
            "May test whether the future-field morphology appears on a model "
            "the instrument was not built around.",
            "Uses the model's own generated trace on the same floor-sum task; "
            "it is not a fixed-prefix Qwen-to-Llama probe.",
            "May not support a generality law; one cross-family model is one "
            "data point.",
        ),
    ),
    "custom": ModelPreset(
        "",
        "custom model",
        True,
        (
            "Records the model id loudly so the claim boundary can be written "
            "before interpretation.",
            "The claim ceiling depends on the selected model, task, projection, "
            "and sampler.",
        ),
    ),
}

RIGOR_PRESETS: dict[str, RigorPreset] = {
    "smoke_budget": RigorPreset(
        "smoke budget (minimal rollouts)",
        SMOKE_PLAN,
        checkpointed=True,
    ),
    "standard": RigorPreset(
        "standard (predeclared depth plan, checkpointed)",
        PREDECLARED_PLAN,
        checkpointed=True,
    ),
    "research": RigorPreset(
        "research-grade (predeclared, revision-pinned, checkpointed)",
        PREDECLARED_PLAN,
        checkpointed=True,
    ),
}

DEFAULT_RIGOR = {
    "smoke": "smoke_budget",
    "paper_family": "research",
    "cross_family": "research",
    "custom": "standard",
}


@dataclass(frozen=True)
class RunContract:
    """A complete declared run configuration for the quickstart notebook."""

    tier: str
    rigor_key: str
    model_id: str
    role: str
    gated: bool
    claim_ceiling: tuple[str, ...]
    revision: str | None
    allow_unpinned: bool
    out_dir: str
    device: str | None
    torch_dtype: str
    prompt: str = FLOORSUM_PROMPT
    answer: int = FLOORSUM_ANSWER
    trace_sampler: SamplerPolicy = TRACE_SAMPLER
    rollout_sampler: SamplerPolicy = ROLLOUT_SAMPLER
    base_seed: int = BASE_SEED
    checkpointed: bool = True
    projection_pack: str | None = None   # pack dir path OR builtin name; None -> ExactMatch

    @property
    def confirm_token(self) -> str:
        return confirm_token_for(self.model_id)

    @property
    def revision_required(self) -> bool:
        return MODEL_PRESETS.get(self.tier, MODEL_PRESETS["custom"]).requires_revision

    def depth_plan(self) -> list[DepthSpec]:
        return [DepthSpec(fraction, rollouts) for fraction, rollouts in self.plan_tuples]

    @property
    def plan_tuples(self) -> tuple[tuple[float, int], ...]:
        return RIGOR_PRESETS[self.rigor_key].plan

    def load_pack(self):
        """Load the declared projection pack, or return None if this run uses none."""
        if not self.projection_pack:
            return None
        from .projection_pack import load_projection_pack, resolve_pack
        return load_projection_pack(resolve_pack(self.projection_pack))

    def projection(self):
        """The run's projection: the declared pack if set, else ExactMatch(answer)."""
        pack = self.load_pack()
        return pack if pack is not None else ExactMatch(self.answer)

    def run_card(self, *, hf_token_status: str = "not checked") -> str:
        return render_run_card(self, hf_token_status=hf_token_status)


def confirm_token_for(model_id: str) -> str:
    """Return a model-specific confirmation token."""

    slug = re.sub(r"[^A-Z0-9]+", "_", model_id.upper()).strip("_")
    return "RUN_" + (slug or "MODEL")


def build_run_contract(
    *,
    tier: str | None,
    rigor_key: str | None = None,
    revision: str | None = None,
    out_dir: str = "reachscan_run",
    custom_model_id: str | None = None,
    device: str | None = None,
    torch_dtype: str = "auto",
    allow_unpinned: bool = False,
    projection_pack: str | None = None,
) -> RunContract:
    """Build a declared run contract.

    Passing ``tier=None`` is a hard error by design. A hidden default model was
    the failure mode this module exists to prevent.
    """

    if tier is None:
        raise SystemExit(
            "No TIER selected. Choose one of "
            f"{list(MODEL_PRESETS)} before running the notebook."
        )
    if tier not in MODEL_PRESETS:
        raise SystemExit(f"Unknown TIER {tier!r}. Choose one of: {list(MODEL_PRESETS)}")

    preset = MODEL_PRESETS[tier]
    model_id = preset.model_id
    role = preset.role
    if tier == "custom":
        if not custom_model_id:
            raise SystemExit("custom tier: set CUSTOM_MODEL_ID before running.")
        model_id = custom_model_id
        role = "custom model"

    rigor_key = rigor_key or DEFAULT_RIGOR[tier]
    if rigor_key not in RIGOR_PRESETS:
        raise SystemExit(
            f"Unknown RIGOR_KEY {rigor_key!r}. Choose one of: {list(RIGOR_PRESETS)}"
        )
    rigor = RIGOR_PRESETS[rigor_key]

    return RunContract(
        tier=tier,
        rigor_key=rigor_key,
        model_id=model_id,
        role=role,
        gated=preset.gated,
        claim_ceiling=preset.claim_ceiling,
        revision=revision,
        allow_unpinned=allow_unpinned,
        out_dir=out_dir,
        device=device,
        torch_dtype=torch_dtype,
        checkpointed=rigor.checkpointed,
        projection_pack=projection_pack,
    )


def _projection_card_lines(contract: "RunContract") -> list[str]:
    """The projection block of the run card: a declared pack, or the ExactMatch
    fallback with a loud claim-ceiling note."""
    if not contract.projection_pack:
        return [
            f"  projection  : ExactMatch({contract.answer})  [NOT a declared pack]",
            "  NOTE        : lens not declared/validated/hashed -> caps this run below",
            "                the pack-backed rungs of the claim ladder",
            "                (set PROJECTION_PACK; see docs/CLAIM_LADDER.md).",
        ]
    try:
        from .projection_pack import validate_fixtures
        pack = contract.load_pack()
    except Exception as exc:  # surfaced here, hard-blocked at confirm
        return [f"  projection  : pack {contract.projection_pack!r} FAILED TO LOAD: {exc}"]
    errs = validate_fixtures(pack)
    ntests = len((pack.prediction or {}).get("tests", []))
    return [
        f"  projection  : pack '{pack.projection_id}' v{pack.projection_version}",
        f"  pack hash   : {pack.pack_hash.value}",
        f"  classes     : {', '.join(pack.declared_classes)}",
        f"  target class: {pack.target_class}",
        f"  claim_level : {pack.claim_level}",
        f"  fixtures    : {'PASS' if not errs else f'FAIL ({len(errs)})'}",
        f"  prediction  : {f'present ({ntests} tests)' if ntests else 'none declared'}",
    ]


def render_run_card(contract: RunContract, *, hf_token_status: str = "not checked") -> str:
    """Render the pre-compute declaration shown in the notebook."""

    total = sum(rollouts for _, rollouts in contract.plan_tuples)
    lines = [
        "=" * 72,
        "  REACHSCAN RUN CARD - read before you confirm",
        "=" * 72,
    ]
    if contract.tier == "smoke":
        lines.append("  *** SMOKE / PIPELINE CHECK - NOT A SCIENTIFIC RESULT ***")
    lines.extend(
        [
            f"  tier        : {contract.tier}",
            f"  model       : {contract.model_id}",
            f"  revision    : {contract.revision or '(UNPINNED)'}",
            f"  role        : {contract.role}",
            f"  gated model : {'yes' if contract.gated else 'no'}",
            f"  HF token    : {hf_token_status}",
            f"  task        : floor-sum (answer {contract.answer})",
        ]
    )
    lines.extend(_projection_card_lines(contract))
    lines.extend(
        [
            f"  rigor       : {RIGOR_PRESETS[contract.rigor_key].label}",
            f"  checkpoint  : {'yes' if contract.checkpointed else 'no'}",
            "  sampler     : T=0.7 top_p=1.0 top_k=None rep=1.0 max_new=512",
            "  depth plan  : "
            + "  ".join(f"{fraction:g}x{rollouts}" for fraction, rollouts in contract.plan_tuples)
            + f"    (total {total} rollouts)",
            f"  out dir     : {contract.out_dir}",
        ]
    )
    if contract.revision_required and not contract.revision:
        lines.append(
            "  revision pin: REQUIRED for this tier; set REVISION to a model commit "
            "SHA or set ALLOW_UNPINNED=True with a documented reason."
        )
    lines.extend(["-" * 72, "  CLAIM CEILING:"])
    for claim in contract.claim_ceiling:
        lines.append(f"    - {claim}")
    lines.extend(
        [
            "-" * 72,
            f"  To proceed, type exactly: {contract.confirm_token}",
            "=" * 72,
        ]
    )
    return "\n".join(lines)


def confirm_run_contract(contract: RunContract, *, typed: str | None = None) -> None:
    """Require the model-specific confirmation token and revision discipline."""

    if typed is None:
        typed = input("\nconfirm > ").strip()
    if typed != contract.confirm_token:
        raise SystemExit(
            f"NOT confirmed (got {typed!r}, expected {contract.confirm_token!r}). "
            "Nothing ran."
        )
    if contract.revision_required and not contract.revision and not contract.allow_unpinned:
        raise SystemExit(
            "Revision pin required for this tier. Set REVISION to a Hugging Face "
            "model commit SHA, or set ALLOW_UNPINNED=True and record the reason "
            "in docs/experiments/run_ledger.md before interpreting results."
        )
    # Enforce the projection-pack lens: it must load and its fixtures must pass
    # before a claim-bearing run proceeds.
    if contract.projection_pack:
        from .projection_pack import validate_fixtures
        try:
            pack = contract.load_pack()
        except Exception as exc:
            raise SystemExit(f"projection pack failed to load: {exc}")
        errs = validate_fixtures(pack)
        if errs:
            raise SystemExit(
                "projection pack fixtures FAILED; fix before running:\n  - "
                + "\n  - ".join(errs)
            )


def detect_hf_token_status() -> str:
    """Best-effort Hugging Face auth status for the run card."""

    if os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN"):
        return "present in environment"
    try:
        from huggingface_hub import HfFolder

        return "present in Hugging Face cache" if HfFolder.get_token() else "missing"
    except Exception:
        return "not checked (huggingface_hub unavailable)"


def load_hf_source(contract: RunContract):
    """Construct the HuggingFace source after the run card is confirmed."""

    from .hf_source import HuggingFaceSource

    return HuggingFaceSource(
        contract.model_id,
        device=contract.device,
        torch_dtype=contract.torch_dtype,
        revision=contract.revision,
    )


def runtime_provenance(source: Any, contract: RunContract) -> dict[str, Any]:
    """Collect runtime facts for the run directory."""

    doc: dict[str, Any] = {
        "tier": contract.tier,
        "rigor": contract.rigor_key,
        "model_id": contract.model_id,
        "source": getattr(source, "name", None),
        "revision": contract.revision,
        "allow_unpinned": contract.allow_unpinned,
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    try:
        import transformers

        doc["transformers"] = transformers.__version__
    except Exception as exc:
        doc["transformers"] = f"unavailable: {exc!r}"
    try:
        import torch

        doc["torch"] = torch.__version__
        doc["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            doc["gpu"] = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            doc["gpu_memory_gb"] = round(props.total_memory / 1024**3, 2)
            doc["gpu_allocated_gb"] = round(torch.cuda.memory_allocated(0) / 1024**3, 2)
            doc["gpu_reserved_gb"] = round(torch.cuda.memory_reserved(0) / 1024**3, 2)
    except Exception as exc:
        doc["torch"] = f"unavailable: {exc!r}"
    model = getattr(source, "_model", None)
    doc["model_device"] = str(getattr(model, "device", None))
    doc["hf_device_map"] = getattr(model, "hf_device_map", None)
    return doc


def write_runtime_provenance(path: str | Path, source: Any, contract: RunContract) -> Path:
    """Write runtime provenance to ``path``."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(runtime_provenance(source, contract), indent=2), encoding="utf-8")
    return path
