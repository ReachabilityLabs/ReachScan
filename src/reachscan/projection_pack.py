"""Projection packs (v0.3.0) — make the task lens executable and auditable.

A projection pack is a directory that declares a task-specific answer lens
precisely enough that ReachScan can run, validate, and bind it into receipts and
the manifest:

    examples/projections/floor_sum_mod8/
      projection.yaml   # ids, version, target, parser/checker/classifier, classes
      adapter.py        # parse(), is_correct(), classify()
      fixtures.jsonl    # labeled rows that pin parser + classifier behavior
      README.md

The pack is hashed over its BEHAVIOR-BEARING files (projection.yaml + adapter.py +
fixtures.jsonl), not the YAML alone — so a parser/classifier change cannot keep
the same hash (see pack_hash_contract). A loaded pack also satisfies the engine's
Projection protocol (extract/project/is_target), so `reach_scan` runs a pack with
no engine changes.

This module is the v2.1 handoff's Phases 1-2. The prediction evaluator (Phase 4)
is intentionally NOT here yet.

YAML is an optional dependency: install `reachscan[projection]`. The engine core
stays dependency-free; only pack loading needs PyYAML.
"""
from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from .contracts import ExtractedAnswer

DEFAULT_HASH_SCOPE = ("projection.yaml", "adapter.py", "fixtures.jsonl")

NO_ANSWER_CLASS = "no_answer"
INVALID_CLASS = "invalid"


# --------------------------------------------------------------------------
# Behavior-bearing pack hash (port of pack_hash_protocol.py)
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class PackHash:
    algorithm: str
    digest: str
    scope: tuple[str, ...]

    @property
    def value(self) -> str:
        return f"{self.algorithm}:{self.digest}"


def hash_projection_pack(pack_dir: Path | str,
                         scope: Iterable[str] = DEFAULT_HASH_SCOPE) -> PackHash:
    """Hash behavior-bearing pack files by relative path AND bytes.

    Hashing the relative path as well as the bytes prevents two same-content files
    from being swapped silently. The scope is sorted so the digest is order-stable.
    """
    base = Path(pack_dir)
    rels = tuple(sorted(scope))
    digest = sha256()
    for rel in rels:
        path = base / rel
        if not path.is_file():
            raise FileNotFoundError(f"missing hash-scope file: {rel}")
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return PackHash("sha256", digest.hexdigest(), rels)


# --------------------------------------------------------------------------
# Fixture rows (port of projection_protocol.py)
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class ProjectionFixture:
    raw_text: str
    parsed_answer: object | None
    target_hit: bool
    projection_class: str


# --------------------------------------------------------------------------
# The loaded pack — also an engine Projection
# --------------------------------------------------------------------------
class ProjectionPack:
    """A loaded projection pack. Carries the declared lens + `pack_meta` for the
    manifest, and bridges to the engine Projection protocol so `reach_scan` can
    use it directly.

    Spec surface (operates on parsed answers): parse / is_correct / classify.
    Engine surface (operates on ExtractedAnswer): extract / project / is_target.
    """

    def __init__(self, *, spec: dict, pack_dir: Path, parse_fn: Callable,
                 is_correct_fn: Callable, classify_fn: Callable, pack_hash: PackHash):
        self._spec = spec
        self._dir = pack_dir
        self._parse = parse_fn
        self._is_correct = is_correct_fn
        self._classify = classify_fn

        self.projection_id: str = spec["projection_id"]
        self.projection_version: str = str(spec["projection_version"])
        self.task_family: str = spec.get("task_family", "")
        self.answer_space_type: str = spec.get("answer_space_type", "")
        self.claim_level: str = spec.get("claim_level", "morphology_demo")
        proj = spec.get("projection", {})
        self.target_class: str = proj["target_class"]
        self.declared_classes: tuple[str, ...] = tuple(proj.get("classes", ()))
        self.target: dict = spec.get("target", {})
        # Engine Projection.name:
        self.name = self.projection_id

        self.pack_hash = pack_hash
        self.pack_meta: dict[str, Any] = {
            "projection_id": self.projection_id,
            "projection_version": self.projection_version,
            "projection_pack_hash": pack_hash.value,
            "projection_pack_hash_scope": list(pack_hash.scope),
            "task_family": self.task_family,
            "answer_space_type": self.answer_space_type,
            "target": self.target,
            "target_class": self.target_class,
            "declared_classes": list(self.declared_classes),
            "claim_level": self.claim_level,
            "parser_name": spec.get("parser", {}).get("name"),
            "checker_name": spec.get("outcome_checker", {}).get("name"),
            "classifier_name": proj.get("name"),
            "fixtures_validated": False,  # set True by validate_fixtures()
        }

        if self.target_class not in self.declared_classes:
            raise ValueError(
                f"target_class {self.target_class!r} is not in declared_classes "
                f"{self.declared_classes!r}")

    # ----- spec surface -----
    def parse(self, raw_text: str) -> object | None:
        return self._parse(raw_text)

    def is_correct(self, parsed_answer: object | None) -> bool:
        return bool(self._is_correct(parsed_answer))

    def classify(self, parsed_answer: object | None) -> str:
        klass = self._classify(parsed_answer)
        if klass not in self.declared_classes:
            raise ValueError(
                f"projection {self.projection_id} emitted undeclared class "
                f"{klass!r}; declared: {self.declared_classes!r}")
        return klass

    # ----- engine Projection surface -----
    def extract(self, completion_text: str) -> ExtractedAnswer:
        parsed = self._parse(completion_text)
        if parsed is None:
            return ExtractedAnswer(ExtractedAnswer.NO_ANSWER, None, completion_text)
        return ExtractedAnswer(ExtractedAnswer.OK, str(parsed), completion_text)

    def project(self, answer: ExtractedAnswer):
        return self.classify(self._parse(answer.raw_text))

    def is_target(self, answer: ExtractedAnswer) -> bool:
        # Consistency rule: target membership is a property of the project() class.
        return self.project(answer) == self.target_class


# --------------------------------------------------------------------------
# Loading + validation
# --------------------------------------------------------------------------
def _require_yaml():
    try:
        import yaml  # noqa: F401
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ImportError(
            "projection packs need PyYAML. Install `reachscan[projection]` "
            "(or `pip install pyyaml`)."
        ) from exc
    return yaml


def _load_adapter(pack_dir: Path):
    adapter_path = pack_dir / "adapter.py"
    if not adapter_path.is_file():
        raise FileNotFoundError(f"pack is missing adapter.py: {adapter_path}")
    spec = importlib.util.spec_from_file_location(
        f"reachscan_pack_{pack_dir.name}", adapter_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _bind(module, block: dict, default: str):
    fn_name = (block or {}).get("function", default)
    fn = getattr(module, fn_name, None)
    if not callable(fn):
        raise AttributeError(f"adapter has no callable {fn_name!r}")
    return fn


def load_projection_pack(pack_dir: Path | str) -> ProjectionPack:
    """Load a projection pack directory into a ProjectionPack."""
    yaml = _require_yaml()
    pack_dir = Path(pack_dir)
    yaml_path = pack_dir / "projection.yaml"
    if not yaml_path.is_file():
        raise FileNotFoundError(f"pack is missing projection.yaml: {yaml_path}")
    spec = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

    module = _load_adapter(pack_dir)
    parse_fn = _bind(module, spec.get("parser"), "parse")
    is_correct_fn = _bind(module, spec.get("outcome_checker"), "is_correct")
    classify_fn = _bind(module, spec.get("projection"), "classify")

    scope = tuple((spec.get("hash", {}) or {}).get("scope", DEFAULT_HASH_SCOPE))
    pack_hash = hash_projection_pack(pack_dir, scope)

    return ProjectionPack(spec=spec, pack_dir=pack_dir, parse_fn=parse_fn,
                          is_correct_fn=is_correct_fn, classify_fn=classify_fn,
                          pack_hash=pack_hash)


def load_fixtures(pack_dir: Path | str) -> list[ProjectionFixture]:
    path = Path(pack_dir) / "fixtures.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"pack is missing fixtures.jsonl: {path}")
    rows: list[ProjectionFixture] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        rows.append(ProjectionFixture(
            raw_text=d["raw_text"], parsed_answer=d.get("parsed_answer"),
            target_hit=bool(d["target_hit"]), projection_class=d["projection_class"]))
    if not rows:
        raise ValueError(f"fixtures.jsonl is empty: {path}")
    return rows


def validate_fixtures(pack: ProjectionPack,
                      fixtures: Sequence[ProjectionFixture] | None = None) -> list[str]:
    """Return validation errors; an empty list means the pack passed.

    On success the pack's `pack_meta["fixtures_validated"]` flips to True so the
    manifest can record that validation ran before the claim-bearing run.
    """
    if fixtures is None:
        fixtures = load_fixtures(pack._dir)

    errors: list[str] = []
    if pack.target_class not in pack.declared_classes:
        errors.append(f"target_class {pack.target_class!r} not in declared_classes")

    for i, fx in enumerate(fixtures, start=1):
        parsed = pack.parse(fx.raw_text)
        if parsed != fx.parsed_answer:
            errors.append(f"fixture {i}: parsed_answer expected {fx.parsed_answer!r}, "
                          f"got {parsed!r}")
        try:
            klass = pack.classify(parsed)
        except ValueError as exc:
            errors.append(f"fixture {i}: {exc}")
            continue
        if klass != fx.projection_class:
            errors.append(f"fixture {i}: projection_class expected "
                          f"{fx.projection_class!r}, got {klass!r}")
        if pack.is_correct(parsed) != fx.target_hit:
            errors.append(f"fixture {i}: target_hit expected {fx.target_hit!r}, "
                          f"got {pack.is_correct(parsed)!r}")

    if not errors:
        pack.pack_meta["fixtures_validated"] = True
    return errors
