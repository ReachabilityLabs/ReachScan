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


# --------------------------------------------------------------------------
# v0.3.2 — pack-aware run contracts
# --------------------------------------------------------------------------
import shutil  # noqa: E402

from reachscan.projection_pack import (  # noqa: E402
    ProjectionPack,
    builtin_pack_path,
)

REPO = Path(__file__).resolve().parents[1]


def test_pack_backed_contract_shows_pack_fields_and_returns_pack():
    c = build_run_contract(tier="cross_family", revision="abc123",
                           projection_pack="floor_sum_mod8")
    assert isinstance(c.projection(), ProjectionPack)
    card = c.run_card()
    assert "pack 'floor_sum_mod8'" in card
    assert "target class: residue_4" in card
    assert "claim_level : morphology_demo" in card
    assert "fixtures    : PASS" in card
    assert "prediction  : present (3 tests)" in card
    assert "projection_pack_hash" not in card  # shows the value, not the literal key
    assert "sha256:" in card


def test_no_pack_contract_warns_about_claim_ceiling():
    c = build_run_contract(tier="smoke")
    card = c.run_card()
    assert "NOT a declared pack" in card
    assert "claim ladder" in card
    from reachscan import ExactMatch
    assert isinstance(c.projection(), ExactMatch)


def test_confirm_blocks_on_failing_pack_fixtures(tmp_path):
    bad = tmp_path / "pack"
    shutil.copytree(builtin_pack_path("floor_sum_mod8"), bad)
    (bad / "adapter.py").write_text(
        "def parse(t): return 1\n"
        "def is_correct(p): return False\n"
        "def classify(p): return 'residue_0'\n")
    c = build_run_contract(tier="smoke", projection_pack=str(bad))
    with pytest.raises(SystemExit, match="fixtures FAILED"):
        confirm_run_contract(c, typed=c.confirm_token)


def test_builtin_pack_matches_example_copy():
    # The packaged (installable) pack must not drift from the examples/ copy.
    pkg = builtin_pack_path("floor_sum_mod8")
    ex = REPO / "examples" / "projections" / "floor_sum_mod8"
    for f in ("projection.yaml", "adapter.py", "fixtures.jsonl"):
        assert (pkg / f).read_bytes() == (ex / f).read_bytes(), f"{f} drifted"
