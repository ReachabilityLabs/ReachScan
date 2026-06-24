"""Prediction evaluator (v0.3.1).

Turns a pack's predeclared `prediction` block into a mechanical
`supported / failed / inconclusive` verdict computed from RAW receipts:

  - prediction evaluation is separate from projection validation;
  - `any_test_failed` is the only accepted loss rule (others -> inconclusive);
  - source-arm filtering is explicit;
  - `expected_mode` is live configuration (concentrated / diffuse / mixed);
  - `family_before_atom` has an initial target-viability precondition and scores
    over parsed (ok) answers only;
  - thin data returns `inconclusive`, never `supported`.

The three test types read WRONG-answer morphology over the declared projection
classes (not target foreclosure): does the family-grain field concentrate, is it
capture vs shatter, and does the family collapse before any single atom wins.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from math import log2
from pathlib import Path
from typing import Any, Mapping, Sequence

SUPPORTED = "supported"
FAILED = "failed"
INCONCLUSIVE = "inconclusive"

DEFAULT_EXCLUDE = ("no_answer", "invalid")


# --------------------------------------------------------------------------
# Verdict containers
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class TestVerdict:
    test_id: str
    test_type: str
    outcome: str
    statistic: float | None
    threshold: float | None
    n_effective: int
    detail: str

    def to_dict(self) -> dict:
        return {"test_id": self.test_id, "test_type": self.test_type,
                "outcome": self.outcome, "statistic": self.statistic,
                "threshold": self.threshold, "n_effective": self.n_effective,
                "detail": self.detail}


@dataclass(frozen=True)
class RunVerdict:
    outcome: str
    loss_rule: str
    tests: list

    def to_dict(self) -> dict:
        return {"outcome": self.outcome, "loss_rule": self.loss_rule,
                "tests": [t.to_dict() for t in self.tests]}


# --------------------------------------------------------------------------
# Hashing the prediction block (identifies the test inside the pack)
# --------------------------------------------------------------------------
def prediction_hash(prediction: Mapping[str, Any]) -> str:
    canon = json.dumps(prediction, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + sha256(canon.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Row helpers
# --------------------------------------------------------------------------
def rows_from_result(result) -> list[dict]:
    """Convert a ReachScanResult's receipts into the evaluator's row dicts."""
    rows = []
    for r in result.receipts:
        rows.append({
            "depth_fraction": float(r.fraction),
            "projection_class": r.projection_class,
            "parsed_answer": r.parsed_answer,
            "target_hit": bool(r.target_hit),
            "parse_status": r.parse_status,
            "source_arm": r.source_arm or "any",
        })
    return rows


def _filter_scope(receipts: Sequence[Mapping], applies_to: Mapping) -> list:
    arm = (applies_to or {}).get("source_arm", "any")
    if arm in (None, "any"):
        return list(receipts)
    return [r for r in receipts if r.get("source_arm") == arm]


def _band(receipts, lo: float, hi: float) -> list:
    return [r for r in receipts if lo <= float(r["depth_fraction"]) <= hi]


def _wrong_ok(rows) -> list:
    return [r for r in rows
            if not bool(r["target_hit"]) and r.get("parse_status", "ok") == "ok"]


def _norm_entropy(counts: Counter, n_support: int) -> float:
    total = sum(counts.values())
    if total == 0 or n_support <= 1:
        return 0.0
    h = -sum((c / total) * log2(c / total) for c in counts.values() if c)
    return h / log2(n_support)


def _structural_classes(declared_classes, target_class, spec) -> list:
    exclude = set(spec.get("exclude_classes", DEFAULT_EXCLUDE))
    return [c for c in declared_classes if c != target_class and c not in exclude]


def _threshold_for_mode(expected_mode, min_entropy, max_entropy):
    if expected_mode == "concentrated":
        return max_entropy
    if expected_mode == "diffuse":
        return min_entropy
    return None


# --------------------------------------------------------------------------
# Test types
# --------------------------------------------------------------------------
def _test_family_structure(receipts, spec, declared_classes, target_class) -> TestVerdict:
    lo, hi = spec.get("depth_band", [0.0, 1.0])
    min_n = int(spec.get("min_n", 30))
    expected_mode = str(spec.get("expected_mode", "concentrated"))
    max_entropy = float(spec.get("max_entropy", 0.75))
    min_entropy = float(spec.get("min_entropy", spec.get("shatter_min", 0.85)))
    structural = set(_structural_classes(declared_classes, target_class, spec))

    rows = [r for r in _wrong_ok(_band(receipts, lo, hi))
            if r["projection_class"] in structural]
    n = len(rows)
    tid = str(spec["id"])
    if n < min_n:
        return TestVerdict(tid, "family_structure", INCONCLUSIVE, None,
                           _threshold_for_mode(expected_mode, min_entropy, max_entropy),
                           n, f"only {n} structural wrong answers in band; need {min_n}")

    h = _norm_entropy(Counter(r["projection_class"] for r in rows), len(structural))
    if expected_mode == "concentrated":
        outcome = SUPPORTED if h <= max_entropy else FAILED
        threshold = max_entropy
        detail = f"expected concentrated; entropy {h:.3f}; max {max_entropy:.3f}"
    elif expected_mode == "diffuse":
        outcome = SUPPORTED if h >= min_entropy else FAILED
        threshold = min_entropy
        detail = f"expected diffuse; entropy {h:.3f}; min {min_entropy:.3f}"
    elif expected_mode == "mixed":
        outcome = SUPPORTED if max_entropy < h < min_entropy else FAILED
        threshold = None
        detail = f"expected mixed; entropy {h:.3f}; range ({max_entropy:.3f}, {min_entropy:.3f})"
    else:
        return TestVerdict(tid, "family_structure", INCONCLUSIVE, h, None, n,
                           f"unsupported expected_mode {expected_mode!r}")
    return TestVerdict(tid, "family_structure", outcome, h, threshold, n, detail)


def _test_morphology_mode(receipts, spec, declared_classes, target_class) -> TestVerdict:
    lo, hi = spec.get("depth_band", [0.85, 1.0])
    min_n = int(spec.get("min_n", 30))
    predicted = str(spec["predicted_mode"])
    capture_max = float(spec.get("capture_max", 0.55))
    shatter_min = float(spec.get("shatter_min", 0.85))
    structural = set(_structural_classes(declared_classes, target_class, spec))

    rows = [r for r in _wrong_ok(_band(receipts, lo, hi))
            if r["projection_class"] in structural]
    n = len(rows)
    tid = str(spec["id"])
    if n < min_n:
        return TestVerdict(tid, "morphology_mode", INCONCLUSIVE, None, None, n,
                           f"only {n} structural wrong answers in band; need {min_n}")

    h = _norm_entropy(Counter(r["projection_class"] for r in rows), len(structural))
    if h <= capture_max:
        observed = "capture"
    elif h >= shatter_min:
        observed = "shatter"
    else:
        observed = "mixed"

    if observed == "mixed" and predicted != "mixed":
        outcome = INCONCLUSIVE
    else:
        outcome = SUPPORTED if observed == predicted else FAILED
    return TestVerdict(tid, "morphology_mode", outcome, h, None, n,
                       f"observed {observed}; predicted {predicted}; entropy {h:.3f}")


def _test_family_before_atom(receipts, spec, declared_classes, target_class) -> TestVerdict:
    _ = declared_classes
    tau_family = float(spec.get("family_collapsed_below", 0.20))
    tau_atom = float(spec.get("atom_won_above", 0.55))
    min_n = int(spec.get("min_n_per_depth", 30))
    initial_target_min = float(spec.get("require_initial_target_mass_above", 0.0))
    tid = str(spec["id"])

    # A usable depth needs enough PARSED (ok) answers. A depth dominated by
    # no_answer/invalid cannot speak to morphology — extraction/yield failure is
    # not a family collapse — so masses are computed over ok rows only, and a
    # depth without min_n ok rows is dropped (thin/failed yield -> inconclusive).
    ok_by_depth: dict[float, list] = defaultdict(list)
    for row in receipts:
        if row.get("parse_status", "ok") == "ok":
            ok_by_depth[float(row["depth_fraction"])].append(row)
    depths = [d for d in sorted(ok_by_depth) if len(ok_by_depth[d]) >= min_n]
    if len(depths) < 2:
        return TestVerdict(tid, "family_before_atom", INCONCLUSIVE, None, None,
                           len(depths), "too few depths with enough parsed (ok) answers")

    first_rows = ok_by_depth[depths[0]]
    first_target_mass = sum(
        1 for r in first_rows if r["projection_class"] == target_class) / len(first_rows)
    if first_target_mass < initial_target_min:
        return TestVerdict(tid, "family_before_atom", INCONCLUSIVE, first_target_mass,
                           initial_target_min, len(first_rows),
                           "target mass already below viability threshold at first usable depth")

    family_depth = None
    atom_depth = None
    for depth in depths:
        rows = ok_by_depth[depth]                       # ok answers only
        target_mass = sum(
            1 for r in rows if r["projection_class"] == target_class) / len(rows)
        wrong = [r for r in rows if not bool(r["target_hit"])]
        atom_mass = 0.0
        if wrong:
            atom_mass = max(Counter(r["parsed_answer"] for r in wrong).values()) / len(wrong)
        if family_depth is None and target_mass < tau_family:
            family_depth = depth
        if atom_depth is None and atom_mass >= tau_atom:
            atom_depth = depth

    if family_depth is None:
        return TestVerdict(tid, "family_before_atom", INCONCLUSIVE, None, tau_family,
                           len(depths), "family never collapsed in observed range")
    gap = None if atom_depth is None else atom_depth - family_depth
    outcome = SUPPORTED if atom_depth is None or family_depth < atom_depth else FAILED
    return TestVerdict(tid, "family_before_atom", outcome, gap, None, len(depths),
                       f"family_depth={family_depth}; atom_depth={atom_depth}; gap={gap}")


TEST_REGISTRY = {
    "family_structure": _test_family_structure,
    "morphology_mode": _test_morphology_mode,
    "family_before_atom": _test_family_before_atom,
}


# --------------------------------------------------------------------------
# Top-level evaluation
# --------------------------------------------------------------------------
def evaluate_prediction(receipts: Sequence[Mapping], prediction: Mapping,
                        declared_classes: Sequence[str], target_class: str) -> RunVerdict:
    """Evaluate a prediction over raw receipt rows; return the run verdict."""
    loss_rule = str(prediction.get("loss_rule", "any_test_failed"))
    if loss_rule != "any_test_failed":
        return RunVerdict(INCONCLUSIVE, loss_rule, [TestVerdict(
            "loss_rule", "configuration", INCONCLUSIVE, None, None, 0,
            f"unsupported loss_rule {loss_rule!r}")])

    scoped = _filter_scope(receipts, prediction.get("applies_to", {}))
    verdicts: list[TestVerdict] = []
    for spec in prediction.get("tests", []):
        test_type = str(spec["type"])
        fn = TEST_REGISTRY.get(test_type)
        if fn is None:
            verdicts.append(TestVerdict(str(spec.get("id", "?")), test_type, INCONCLUSIVE,
                                        None, None, 0, f"unknown test type {test_type!r}"))
            continue
        verdicts.append(fn(scoped, spec, declared_classes, target_class))

    if any(v.outcome == FAILED for v in verdicts):
        outcome = FAILED
    elif any(v.outcome == INCONCLUSIVE for v in verdicts):
        outcome = INCONCLUSIVE
    else:
        outcome = SUPPORTED
    return RunVerdict(outcome, loss_rule, verdicts)


def evaluate_run(pack, result) -> RunVerdict:
    """Evaluate a loaded pack's prediction block against a ReachScanResult."""
    prediction = pack.prediction
    if not prediction:
        raise ValueError(f"pack {pack.projection_id} has no prediction block to evaluate")
    return evaluate_prediction(rows_from_result(result), prediction,
                               pack.declared_classes, pack.target_class)


# --------------------------------------------------------------------------
# Verdict artifact + manifest update
# --------------------------------------------------------------------------
def write_prediction_verdict(verdict: RunVerdict, outdir: str | Path, *,
                             prediction: Mapping, pack, run_meta: Mapping | None = None,
                             evaluated_utc: str | None = None) -> Path:
    from .metadata import write_companion_meta

    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    p_hash = prediction_hash(prediction)
    source_name = str((run_meta or {}).get("source", "")).lower()
    honesty = [
        "Verdict computed from raw receipts; sampler- and projection-relative.",
        "A zero/thin-evidence test is INCONCLUSIVE, never a false support/fail.",
        "Wrong-answer morphology under one model/task/sampler is not generality.",
    ]
    if "mock" in source_name:
        honesty.insert(0, "SOURCE IS A MOCK FIXTURE — mechanism demonstration, not a result.")

    doc = {
        "outcome": verdict.outcome,
        "loss_rule": verdict.loss_rule,
        "prediction_hash": p_hash,
        "projection_id": pack.projection_id,
        "projection_pack_hash": pack.pack_hash.value,
        "evaluated_utc": evaluated_utc or datetime.now(timezone.utc).isoformat(),
        "run": dict(run_meta or {}),
        "tests": [t.to_dict() for t in verdict.tests],
        "honesty": honesty,
    }
    path = outdir / "prediction_verdict.json"
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    write_companion_meta(path, {"kind": "prediction_verdict", "outcome": verdict.outcome})
    return path


def update_manifest_with_verdict(run_dir: str | Path, verdict: RunVerdict, *,
                                 prediction: Mapping, verdict_path: str = "prediction_verdict.json") -> None:
    """Record the prediction hash, tests, verdict path, and outcome in the manifest."""
    run_dir = Path(run_dir)
    mpath = run_dir / "run_manifest.json"
    if not mpath.exists():
        return
    doc = json.loads(mpath.read_text(encoding="utf-8"))
    manifest = doc.get("run_manifest", doc)
    manifest["prediction"] = {
        "prediction_hash": prediction_hash(prediction),
        "loss_rule": verdict.loss_rule,
        "tests": [t.test_id for t in verdict.tests],
        "verdict_path": verdict_path,
        "outcome": verdict.outcome,
    }
    mpath.write_text(json.dumps(doc, indent=2), encoding="utf-8")
