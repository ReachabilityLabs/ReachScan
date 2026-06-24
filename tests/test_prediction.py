"""Tests for the v0.3.1 prediction evaluator (handoff v2.1 Phase 4).

Includes the packaged receipt fixtures (supported / failed / inconclusive /
already-collapsed / source-arm-filtered / diffuse-mode) and the verification-plan
unit checks.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from reachscan import (  # noqa: E402
    DepthSpec,
    GeneratedPrefixSource,
    MockSource,
    SamplerPolicy,
    evaluate_prediction,
    evaluate_run,
    load_projection_pack,
    prediction_hash,
    reach_scan,
    rows_from_result,
)
from reachscan.metadata import write_result  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
PACK = REPO / "examples" / "projections" / "floor_sum_mod8"
CASES = json.loads((Path(__file__).parent / "data"
                    / "prediction_receipt_fixture_cases.json").read_text())
PROMPT = "Compute the sum of floor((3n+7)/5) for n = 1..40."


def _expand(specs):
    rows = []
    for s in specs:
        for off in range(int(s.get("count", 1))):
            start = s.get("parsed_answer_start")
            rows.append({
                "depth_fraction": s["depth_fraction"],
                "projection_class": s["projection_class"],
                "target_hit": s["target_hit"],
                "parse_status": s["parse_status"],
                "source_arm": s.get("source_arm", "any"),
                "parsed_answer": (int(start) + off) if start is not None else s.get("parsed_answer"),
            })
    return rows


# --------------------------------------------------------------------------
# Packaged receipt fixtures — the verdict must match each declared outcome
# --------------------------------------------------------------------------
@pytest.mark.parametrize("case", CASES["cases"], ids=[c["name"] for c in CASES["cases"]])
def test_packaged_fixture_outcomes(case):
    pred = case.get("prediction", CASES["prediction"])
    verdict = evaluate_prediction(_expand(case["rows"]), pred,
                                  CASES["declared_classes"], CASES["target_class"])
    assert verdict.outcome == case["expected_outcome"]


# --------------------------------------------------------------------------
# Verification-plan unit checks
# --------------------------------------------------------------------------
def _base_rows(klass="residue_2", n=40, depth=0.9):
    return _expand([{"count": n, "depth_fraction": depth, "projection_class": klass,
                     "target_hit": False, "parse_status": "ok", "parsed_answer_start": 100}])


def test_unknown_loss_rule_is_inconclusive():
    pred = {"loss_rule": "majority_vote", "tests": []}
    v = evaluate_prediction(_base_rows(), pred, CASES["declared_classes"], "residue_4")
    assert v.outcome == "inconclusive"


def test_unknown_test_type_is_inconclusive():
    pred = {"loss_rule": "any_test_failed",
            "tests": [{"id": "bogus", "type": "no_such_test", "depth_band": [0.85, 1.0]}]}
    v = evaluate_prediction(_base_rows(), pred, CASES["declared_classes"], "residue_4")
    assert v.outcome == "inconclusive"
    assert v.tests[0].outcome == "inconclusive"


def test_expected_mode_diffuse_is_live_config():
    # 7 residues evenly -> high entropy -> diffuse supported, concentrated would fail.
    rows = _expand([{"count": 6, "depth_fraction": 0.9, "projection_class": f"residue_{r}",
                     "target_hit": False, "parse_status": "ok", "parsed_answer_start": 1000 + r}
                    for r in (0, 1, 2, 3, 5, 6, 7)])
    diffuse = {"loss_rule": "any_test_failed", "tests": [
        {"id": "d", "type": "family_structure", "depth_band": [0.85, 1.0],
         "expected_mode": "diffuse", "min_entropy": 0.85, "min_n": 30}]}
    concentrated = {"loss_rule": "any_test_failed", "tests": [
        {"id": "c", "type": "family_structure", "depth_band": [0.85, 1.0],
         "expected_mode": "concentrated", "max_entropy": 0.75, "min_n": 30}]}
    assert evaluate_prediction(rows, diffuse, CASES["declared_classes"], "residue_4").outcome == "supported"
    assert evaluate_prediction(rows, concentrated, CASES["declared_classes"], "residue_4").outcome == "failed"


def test_family_before_atom_requires_initial_viable_target():
    # target already absent at the first usable depth -> inconclusive, not a free pass.
    case = next(c for c in CASES["cases"] if c["name"] == "already_dead_target_inconclusive")
    v = evaluate_prediction(_expand(case["rows"]), CASES["prediction"],
                            CASES["declared_classes"], CASES["target_class"])
    fba = [t for t in v.tests if t.test_type == "family_before_atom"][0]
    assert fba.outcome == "inconclusive"


def test_thin_data_is_inconclusive_never_supported():
    case = next(c for c in CASES["cases"] if c["name"] == "thin_inconclusive")
    v = evaluate_prediction(_expand(case["rows"]), CASES["prediction"],
                            CASES["declared_classes"], CASES["target_class"])
    assert v.outcome == "inconclusive"


# --------------------------------------------------------------------------
# Hashing
# --------------------------------------------------------------------------
def test_prediction_hash_stable_and_threshold_sensitive():
    p = dict(CASES["prediction"])
    assert prediction_hash(p) == prediction_hash(dict(CASES["prediction"]))
    tweaked = json.loads(json.dumps(p))
    tweaked["tests"][0]["max_entropy"] = 0.5
    assert prediction_hash(tweaked) != prediction_hash(p)


# --------------------------------------------------------------------------
# End-to-end on a pack-driven mock run
# --------------------------------------------------------------------------
def _pack_run():
    pack = load_projection_pack(PACK)
    src = MockSource(basin_value=56)
    ps = GeneratedPrefixSource(src, PROMPT, trace_sampler=SamplerPolicy(max_new_tokens=160), seed=0)
    res = reach_scan(source=src, prefix_source=ps, projection=pack,
                     plan=[DepthSpec(f, 60) for f in (0.0, 0.9, 1.0)],
                     rollout_sampler=SamplerPolicy(max_new_tokens=16), base_seed=0,
                     source_arm="natural_trace")
    return pack, res


def test_rows_from_result_shape():
    _, res = _pack_run()
    row = rows_from_result(res)[0]
    assert set(row) >= {"depth_fraction", "projection_class", "target_hit",
                        "parse_status", "parsed_answer", "source_arm"}


def test_evaluate_run_then_cli_writes_verdict_and_manifest(tmp_path):
    from reachscan.tools.cli import main

    pack, res = _pack_run()
    verdict = evaluate_run(pack, res)
    assert verdict.outcome in {"supported", "failed", "inconclusive"}

    run_dir = tmp_path / "run"
    write_result(res, run_dir)
    rc = main(["prediction", "evaluate", str(run_dir), "--projection", str(PACK)])
    assert rc == 0
    doc = json.loads((run_dir / "prediction_verdict.json").read_text())
    assert doc["outcome"] == verdict.outcome
    assert doc["prediction_hash"].startswith("sha256:")
    # manifest now carries the prediction block
    man = json.loads((run_dir / "run_manifest.json").read_text())["run_manifest"]
    assert man["prediction"]["outcome"] == verdict.outcome
    assert man["prediction"]["verdict_path"] == "prediction_verdict.json"


def test_cli_rejects_run_from_a_different_pack(tmp_path):
    from reachscan import ModuloProjection
    from reachscan.tools.cli import main

    src = MockSource(basin_value=56)
    ps = GeneratedPrefixSource(src, PROMPT, trace_sampler=SamplerPolicy(max_new_tokens=120), seed=0)
    res = reach_scan(source=src, prefix_source=ps, projection=ModuloProjection(8, 4),
                     plan=[DepthSpec(0.0, 8), DepthSpec(0.9, 8)],
                     rollout_sampler=SamplerPolicy(max_new_tokens=12), base_seed=0)
    run_dir = tmp_path / "plain"
    write_result(res, run_dir)
    assert main(["prediction", "evaluate", str(run_dir), "--projection", str(PACK)]) == 2
