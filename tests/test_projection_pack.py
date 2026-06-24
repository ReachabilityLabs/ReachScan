"""Tests for v0.3.0 projection packs: pack load + behavior-bearing hash + fixture
validation, the engine bridge, and the receipt/manifest binding."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from reachscan import (  # noqa: E402
    DepthSpec,
    GeneratedPrefixSource,
    ModuloProjection,
    MockSource,
    SamplerPolicy,
    reach_scan,
)
from reachscan.metadata import read_result, write_result  # noqa: E402
from reachscan.projection_pack import (  # noqa: E402
    hash_projection_pack,
    load_fixtures,
    load_projection_pack,
    validate_fixtures,
)

REPO = Path(__file__).resolve().parents[1]
PACK = REPO / "examples" / "projections" / "floor_sum_mod8"
PROMPT = "Compute the sum of floor((3n+7)/5) for n = 1..40."


def _copy_pack(tmp_path) -> Path:
    dst = tmp_path / "pack"
    shutil.copytree(PACK, dst)
    return dst


# --------------------------------------------------------------------------
# Pack loading + behavior-bearing hash
# --------------------------------------------------------------------------
def test_pack_loads_with_declared_lens():
    pack = load_projection_pack(PACK)
    assert pack.projection_id == "floor_sum_mod8"
    assert pack.target_class == "residue_4"
    assert "no_answer" in pack.declared_classes and "invalid" in pack.declared_classes
    assert pack.pack_hash.value.startswith("sha256:")


def test_pack_hash_is_stable():
    assert hash_projection_pack(PACK).value == hash_projection_pack(PACK).value


@pytest.mark.parametrize("fname", ["adapter.py", "fixtures.jsonl", "projection.yaml"])
def test_pack_hash_changes_when_behavior_file_changes(tmp_path, fname):
    pack_dir = _copy_pack(tmp_path)
    before = hash_projection_pack(pack_dir).value
    target = pack_dir / fname
    target.write_text(target.read_text() + "\n# touch\n")
    assert hash_projection_pack(pack_dir).value != before


def test_readme_change_does_not_change_hash(tmp_path):
    pack_dir = _copy_pack(tmp_path)
    before = hash_projection_pack(pack_dir).value
    (pack_dir / "README.md").write_text("# different readme\n")
    assert hash_projection_pack(pack_dir).value == before  # README is out of scope


# --------------------------------------------------------------------------
# Fixture validation
# --------------------------------------------------------------------------
def test_fixtures_validate_and_flip_the_flag():
    pack = load_projection_pack(PACK)
    assert pack.pack_meta["fixtures_validated"] is False
    assert validate_fixtures(pack) == []
    assert pack.pack_meta["fixtures_validated"] is True


def test_broken_parser_fails_fixtures(tmp_path):
    pack_dir = _copy_pack(tmp_path)
    (pack_dir / "adapter.py").write_text(
        "def parse(t): return 999\n"
        "def is_correct(p): return p == 532\n"
        "def classify(p): return 'residue_0'\n")
    pack = load_projection_pack(pack_dir)
    errors = validate_fixtures(pack)
    assert errors and pack.pack_meta["fixtures_validated"] is False


def test_undeclared_class_is_rejected(tmp_path):
    pack_dir = _copy_pack(tmp_path)
    (pack_dir / "adapter.py").write_text(
        "def parse(t): return 532\n"
        "def is_correct(p): return p == 532\n"
        "def classify(p): return 'residue_999'\n")  # not in declared_classes
    pack = load_projection_pack(pack_dir)
    errors = validate_fixtures(pack)
    assert any("undeclared class" in e for e in errors)


def test_target_class_must_be_declared(tmp_path):
    pack_dir = _copy_pack(tmp_path)
    yaml_text = (pack_dir / "projection.yaml").read_text().replace(
        "target_class: residue_4", "target_class: residue_99")
    (pack_dir / "projection.yaml").write_text(yaml_text)
    with pytest.raises(ValueError, match="target_class"):
        load_projection_pack(pack_dir)


# --------------------------------------------------------------------------
# Engine Projection bridge
# --------------------------------------------------------------------------
def test_bridge_separates_target_class_from_exact_answer():
    pack = load_projection_pack(PACK)
    a = pack.extract("The final answer is \\boxed{916}.")  # 916 % 8 == 4
    assert pack.project(a) == "residue_4"
    assert pack.is_target(a) is True            # in the target CLASS
    assert pack.is_correct(pack.parse(a.raw_text)) is False  # but NOT the exact answer


def test_bridge_handles_no_answer_and_invalid():
    pack = load_projection_pack(PACK)
    na = pack.extract("no number here")
    assert na.status == "no_answer"
    inv = pack.extract("The ratio is \\boxed{5/8}.")
    assert inv.is_ok and pack.project(inv) == "invalid"


# --------------------------------------------------------------------------
# Receipt + manifest binding
# --------------------------------------------------------------------------
def _mock_scan(projection, **kw):
    src = MockSource(basin_value=56)
    ps = GeneratedPrefixSource(src, PROMPT, trace_sampler=SamplerPolicy(max_new_tokens=120), seed=0)
    return reach_scan(source=src, prefix_source=ps, projection=projection,
                      plan=[DepthSpec(0.0, 8), DepthSpec(1.0, 8)],
                      rollout_sampler=SamplerPolicy(max_new_tokens=12), base_seed=0, **kw)


def test_pack_run_binds_projection_into_manifest_and_receipts(tmp_path):
    pack = load_projection_pack(PACK)
    validate_fixtures(pack)
    res = _mock_scan(pack, source_arm="natural_trace")

    block = res.manifest["projection_pack"]
    assert block["projection_id"] == "floor_sum_mod8"
    assert block["projection_pack_hash"] == pack.pack_hash.value
    assert block["fixtures_validated"] is True
    assert res.manifest["source_arm"] == "natural_trace"
    assert res.manifest["engine_schema"] == "0.3.0"

    r = res.receipts[0]
    assert r.projection_class and r.projection_class.startswith(("residue_", "no_answer"))
    assert r.projection_id == "floor_sum_mod8"
    assert r.projection_pack_hash == pack.pack_hash.value
    assert r.source_arm == "natural_trace"
    assert r.exposure_check_status == "not_checked"

    # round-trip preserves the projection columns + manifest block
    write_result(res, tmp_path)
    back = read_result(tmp_path)
    assert back.manifest["projection_pack"]["projection_id"] == "floor_sum_mod8"
    assert back.receipts[0].projection_class == r.projection_class
    assert back.receipts[0].projection_id == "floor_sum_mod8"


def test_plain_projection_run_stays_backward_compatible(tmp_path):
    res = _mock_scan(ModuloProjection(8, target_residue=4))
    assert "projection_pack" not in res.manifest          # no pack -> no block
    r = res.receipts[0]
    assert r.projection_id is None                        # run-constants empty
    assert r.projection_class == str(r.bucket)            # class derived from bucket
    write_result(res, tmp_path)                           # writes + reads without error
    assert read_result(tmp_path).receipts[0].projection_class == r.projection_class


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def test_cli_validate_passes_and_fails(tmp_path):
    from reachscan.tools.cli import main
    assert main(["projection", "validate", str(PACK)]) == 0
    bad = _copy_pack(tmp_path)
    (bad / "adapter.py").write_text(
        "def parse(t): return 1\n"
        "def is_correct(p): return False\n"
        "def classify(p): return 'residue_1'\n")
    assert main(["projection", "validate", str(bad)]) == 1


def test_missing_files_fail_loud(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_projection_pack(tmp_path)  # empty dir: no projection.yaml
    with pytest.raises(FileNotFoundError):
        load_fixtures(tmp_path)
