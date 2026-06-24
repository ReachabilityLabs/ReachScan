"""Tests for the quickstart run-contract gate."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from reachscan.run_contract import (  # noqa: E402
    FLOORSUM_PROMPT,
    MODEL_PRESETS,
    build_run_contract,
    confirm_run_contract,
    confirm_token_for,
)


def test_tier_none_hard_stops():
    with pytest.raises(SystemExit, match="No TIER selected"):
        build_run_contract(tier=None)


def test_cross_family_contract_names_llama_and_is_model_specific():
    contract = build_run_contract(
        tier="cross_family",
        revision="abc123",
    )
    assert contract.model_id == "meta-llama/Llama-3.1-8B-Instruct"
    assert contract.confirm_token == "RUN_META_LLAMA_LLAMA_3_1_8B_INSTRUCT"
    assert contract.confirm_token != confirm_token_for(MODEL_PRESETS["smoke"].model_id)
    assert "Qwen/Qwen2.5-1.5B-Instruct" not in contract.run_card()


def test_smoke_card_is_not_claim_bearing():
    contract = build_run_contract(tier="smoke")
    card = contract.run_card(hf_token_status="missing")
    assert "NOT A SCIENTIFIC RESULT" in card
    assert "May not support a scientific claim" in card


def test_real_tier_requires_revision_pin_unless_explicitly_overridden():
    contract = build_run_contract(tier="cross_family")
    with pytest.raises(SystemExit, match="Revision pin required"):
        confirm_run_contract(contract, typed=contract.confirm_token)

    overridden = build_run_contract(tier="cross_family", allow_unpinned=True)
    confirm_run_contract(overridden, typed=overridden.confirm_token)


def test_floor_sum_prompt_preserves_boxed_extraction_contract():
    assert "\\boxed{}" in FLOORSUM_PROMPT
    assert "floor((3n+7)/5)" in FLOORSUM_PROMPT
    assert "n = 1 through n = 40" in FLOORSUM_PROMPT


def test_quickstart_has_no_active_model_id_default():
    notebook = json.loads(Path("notebooks/reachscan_quickstart.ipynb").read_text())
    source_cells = [
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    ]
    assert any("build_run_contract" in cell for cell in source_cells)
    for cell in source_cells:
        active_lines = [
            line.strip()
            for line in cell.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        assert 'MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"' not in active_lines
        assert 'MODEL_ID = "meta-llama/Llama-3.1-8B-Instruct"' not in active_lines
