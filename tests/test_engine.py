"""reachscan engine tests — provable correct with no GPU.

Covers: contract conformance, the future-field math, target reachability,
the per-depth-M plan (R1), the collision-free seed rule and no determinism
collapse (R2), and the prompt-only f=0 row always being present.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from reachscan import (  # noqa: E402
    DepthSpec,
    ExactMatch,
    ExtractedAnswer,
    GeneratedPrefixSource,
    ModuloProjection,
    MockSource,
    PrefixSource,
    Projection,
    SamplerPolicy,
    TargetFiber,
    TokenContinuationSource,
    UserPrefixSource,
    derive_seed,
    reach_scan,
    uniform_plan,
)
from reachscan.engine import shannon_entropy_bits, wilson_interval  # noqa: E402


def test_contract_conformance():
    """Mock/projections/prefix-sources honor their protocols (runtime_checkable)."""
    assert isinstance(MockSource(), TokenContinuationSource)
    assert isinstance(ModuloProjection(8, 4), Projection)
    assert isinstance(ExactMatch(532), Projection)
    assert isinstance(UserPrefixSource([1, 2], [3, 4]), PrefixSource)


def test_seed_no_collision_high_M():
    """R2: collision-free even far above the old 1000 stride."""
    seeds = set()
    for di in range(12):
        for r in range(2000):
            s = derive_seed(42, di, r)
            assert s not in seeds, f"seed collision at depth {di} rollout {r}"
            seeds.add(s)
    assert len(seeds) == 12 * 2000


def test_seed_distinct_within_depth():
    """R2: M rollouts at one depth get M distinct seeds (no determinism collapse)."""
    seeds = {derive_seed(7, 0, r) for r in range(256)}
    assert len(seeds) == 256


def test_mock_not_degenerate():
    """R2 guard: the mock produces >1 distinct outcome at a depth (else the field
    would be an artifactual point mass and the seed rule would be untested)."""
    src = MockSource()
    outcomes = set()
    for r in range(64):
        ids = src.sample_completion(src.encode_prompt("Q"), temperature=0.7,
                                    top_p=1.0, max_new_tokens=16, seed=derive_seed(0, 0, r))
        outcomes.add(src.decode(ids))
    assert len(outcomes) > 1, "mock collapsed to a single outcome"


def test_per_depth_M_plan():
    """R1: a plan with different M per depth is honored exactly."""
    src = MockSource()
    ps = UserPrefixSource(src.encode_prompt("Problem: compute the sum"),
                          src.encode_prompt("step one step two step three step four"))
    proj = ModuloProjection(8, target_residue=4)
    plan = [DepthSpec(0.0, 256), DepthSpec(0.5, 64), DepthSpec(1.0, 128)]
    res = reach_scan(source=src, prefix_source=ps, projection=proj, plan=plan,
                     rollout_sampler=SamplerPolicy(max_new_tokens=16), base_seed=1)
    by_frac = {s.fraction: s for s in res.summaries}
    assert by_frac[0.0].attempts == 256
    assert by_frac[0.5].attempts == 64
    assert by_frac[1.0].attempts == 128


def test_prompt_only_row_always_present():
    """The engine always includes f=0.0 even if the plan omits it."""
    src = MockSource()
    ps = UserPrefixSource(src.encode_prompt("Q"), src.encode_prompt("a b c d"))
    proj = ModuloProjection(8, 4)
    res = reach_scan(source=src, prefix_source=ps, projection=proj,
                     plan=[DepthSpec(0.5, 8)], rollout_sampler=SamplerPolicy(max_new_tokens=16))
    assert any(abs(s.fraction) < 1e-9 for s in res.summaries), "f=0 row missing"


def test_future_field_sums_to_numeric():
    """Field counts over OK answers must sum to the numeric (OK) count."""
    src = MockSource()
    ps = UserPrefixSource(src.encode_prompt("Q"), src.encode_prompt("a b c d e f"))
    proj = ModuloProjection(8, 4)
    res = reach_scan(source=src, prefix_source=ps, projection=proj,
                     plan=uniform_plan([0.0, 0.5, 1.0], 32),
                     rollout_sampler=SamplerPolicy(max_new_tokens=16))
    for s in res.summaries:
        assert sum(s.field.values()) == s.numeric


def test_target_reachability_matches_field():
    """R_T must equal target-bucket mass (project/is_target consistency)."""
    src = MockSource()
    ps = UserPrefixSource(src.encode_prompt("Q"), src.encode_prompt("a b c d"))
    proj = ModuloProjection(8, target_residue=4)  # target bucket is residue 4
    res = reach_scan(source=src, prefix_source=ps, projection=proj,
                     plan=uniform_plan([0.0, 1.0], 64),
                     rollout_sampler=SamplerPolicy(max_new_tokens=16))
    for s in res.summaries:
        mass_in_target_bucket = s.field.get(4, 0) / s.numeric if s.numeric else 0.0
        assert abs(s.target_reachability - mass_in_target_bucket) < 1e-9


def test_foreclosure_shape_detected():
    """The engine should see target reachability DROP as commitment grows on the
    mock (whose field drifts toward the basin). This is a toy analogue of the
    paper's foreclosure, and it verifies the engine actually measures depth trend."""
    src = MockSource(basin_value=56)  # 56 % 8 == 0, NOT the target residue 4
    # Long trace so the drift has room to act.
    ps = UserPrefixSource(src.encode_prompt("Problem"), src.encode_prompt("x" * 400))
    proj = ModuloProjection(8, target_residue=4)
    res = reach_scan(source=src, prefix_source=ps, projection=proj,
                     plan=uniform_plan([0.0, 0.5, 1.0], 200),
                     rollout_sampler=SamplerPolicy(max_new_tokens=16), base_seed=5)
    rt = {s.fraction: s.target_reachability for s in res.summaries}
    assert rt[0.0] >= rt[1.0], f"expected target reachability to fall: {rt}"


def test_status_audit_excludes_nonok_from_field():
    """no_answer / truncated answers count in the denominator audit but not the field."""
    class EmptyProj:
        name = "empty"
        def extract(self, text):
            return ExtractedAnswer(ExtractedAnswer.NO_ANSWER, None, text)
        def project(self, a):
            raise AssertionError("project called on non-ok answer")
        def is_target(self, a):
            raise AssertionError("is_target called on non-ok answer")
    src = MockSource()
    ps = UserPrefixSource(src.encode_prompt("Q"), src.encode_prompt("a b c"))
    res = reach_scan(source=src, prefix_source=ps, projection=EmptyProj(),
                     plan=[DepthSpec(0.0, 10)], rollout_sampler=SamplerPolicy(max_new_tokens=16))
    s = res.summaries[0]
    assert s.numeric == 0 and s.no_answer == 10 and s.field == {}


def test_generated_prefix_source_roundtrip():
    """GeneratedPrefixSource produces a non-empty frozen trace and runs."""
    src = MockSource()
    gps = GeneratedPrefixSource(src, "Problem: compute the sum",
                                trace_sampler=SamplerPolicy(max_new_tokens=32), seed=3)
    assert len(gps.reference_trace_ids()) > 0
    res = reach_scan(source=src, prefix_source=gps, projection=ModuloProjection(8, 4),
                     plan=uniform_plan([0.0, 0.5, 1.0], 16),
                     rollout_sampler=SamplerPolicy(max_new_tokens=16))
    assert len(res.summaries) == 3


def test_wilson_and_entropy_helpers():
    lo, hi = wilson_interval(50, 100)  # symmetric textbook case, p_hat = 0.5
    assert 0.0 < lo < 0.5 < hi < 1.0
    assert 0.38 < lo < 0.42 and 0.58 < hi < 0.62  # standard Wilson 95% interval
    assert abs(shannon_entropy_bits([1, 1, 1, 1]) - 2.0) < 1e-9  # 4 equal buckets = 2 bits
    assert shannon_entropy_bits([10]) == 0.0  # point mass = 0 bits




def _mock_scan(basin):
    from reachscan import (reach_scan, MockSource, GeneratedPrefixSource,
                           ExactMatch, SamplerPolicy, uniform_plan)
    src = MockSource(basin_value=basin)
    pre = GeneratedPrefixSource(src, "p", trace_sampler=SamplerPolicy(max_new_tokens=40), seed=0)
    return reach_scan(source=src, prefix_source=pre, projection=ExactMatch(532),
                      plan=uniform_plan([0.0, 0.9, 1.0], 128),
                      rollout_sampler=SamplerPolicy(max_new_tokens=16), base_seed=0)


def test_source_separation_self_is_zero():
    from reachscan import source_separation
    r = _mock_scan(532)
    for row in source_separation(r, r):
        assert abs(row.separation) < 1e-9
        assert row.sep_low <= 0.0 <= row.sep_high


def test_source_separation_positive_at_depth():
    from reachscan import source_separation
    sep = source_separation(_mock_scan(532), _mock_scan(56))
    deep = [row for row in sep if row.fraction >= 0.9]
    assert deep and any(row.separation > 0 for row in deep)

# ---------------------------------------------------------------------------
# v0.2.1 additions
# ---------------------------------------------------------------------------

def test_sampler_policy_passes_through_plug():
    """The engine must hand the FULL declared policy across the contract (P1)."""
    seen = {}

    class RecordingSource:
        name = "recorder"
        def encode_prompt(self, prompt, *, system=None):
            return [1, 2, 3]
        def decode(self, ids):
            return "\\boxed{4}"
        def sample_completion(self, input_ids, *, temperature, top_p, max_new_tokens,
                              top_k=None, repetition_penalty=1.0,
                              stop_token_ids=None, seed=None, **extras):
            seen.update(temperature=temperature, top_p=top_p, top_k=top_k,
                        repetition_penalty=repetition_penalty)
            return [98, 111]

    src = RecordingSource()
    ps = UserPrefixSource([1, 2, 3], [5, 6, 7, 8])
    pol = SamplerPolicy(temperature=0.6, top_p=0.9, top_k=10,
                        repetition_penalty=1.1, max_new_tokens=8)
    reach_scan(source=src, prefix_source=ps, projection=ModuloProjection(8, 4),
               plan=[DepthSpec(1.0, 2)], rollout_sampler=pol, base_seed=3)
    assert seen == {"temperature": 0.6, "top_p": 0.9, "top_k": 10,
                    "repetition_penalty": 1.1}


def test_cap_hit_flagged_and_counted():
    """Generations that fill max_new_tokens are flagged in receipts and summed (P3)."""
    src = MockSource()
    ps = GeneratedPrefixSource(src, "p" * 40,
                               trace_sampler=SamplerPolicy(max_new_tokens=40), seed=1)
    res = reach_scan(source=src, prefix_source=ps, projection=ModuloProjection(8, 4),
                     plan=[DepthSpec(1.0, 30)],
                     rollout_sampler=SamplerPolicy(max_new_tokens=5), base_seed=1)
    deep = res.summaries[-1]
    assert deep.cap_hits == 30  # 5-char budget always fills
    assert all(r.hit_token_cap for r in res.receipts if r.fraction == 1.0)
    res2 = reach_scan(source=src, prefix_source=ps, projection=ModuloProjection(8, 4),
                      plan=[DepthSpec(1.0, 30)],
                      rollout_sampler=SamplerPolicy(max_new_tokens=64), base_seed=1)
    assert res2.summaries[-1].cap_hits == 0


def test_include_prompt_only_flag():
    src = MockSource()
    ps = GeneratedPrefixSource(src, "p" * 40,
                               trace_sampler=SamplerPolicy(max_new_tokens=40), seed=2)
    res = reach_scan(source=src, prefix_source=ps, projection=ModuloProjection(8, 4),
                     plan=[DepthSpec(0.5, 4)], rollout_sampler=SamplerPolicy(max_new_tokens=16),
                     base_seed=2, include_prompt_only=False)
    assert [s.fraction for s in res.summaries] == [0.5]
    assert res.manifest["include_prompt_only"] is False


def test_committed_len_overrides_fraction():
    """Contract v3 R5: near-terminal anchors are specifiable by COUNT (P7)."""
    src = MockSource()
    ps = GeneratedPrefixSource(src, "p" * 40,
                               trace_sampler=SamplerPolicy(max_new_tokens=40), seed=3)
    L = len(ps.reference_trace_ids())
    res = reach_scan(source=src, prefix_source=ps, projection=ModuloProjection(8, 4),
                     plan=[DepthSpec(0.999, 3, committed_len=L - 1), DepthSpec(1.0, 3)],
                     rollout_sampler=SamplerPolicy(max_new_tokens=16), base_seed=3)
    by_label = {round(s.fraction, 3): s.committed_len for s in res.summaries}
    assert by_label[0.999] == L - 1 and by_label[1.0] == L


def test_plan_validation_fails_loud():
    src = MockSource()
    ps = GeneratedPrefixSource(src, "p" * 40,
                               trace_sampler=SamplerPolicy(max_new_tokens=40), seed=4)
    for bad in ([DepthSpec(1.5, 4)], [DepthSpec(-0.1, 4)], [DepthSpec(0.5, 0)],
                [DepthSpec(0.5, 4, committed_len=10_000)]):
        try:
            reach_scan(source=src, prefix_source=ps, projection=ModuloProjection(8, 4),
                       plan=bad, rollout_sampler=SamplerPolicy(max_new_tokens=16), base_seed=4)
            assert False, f"plan {bad} should have raised"
        except ValueError:
            pass


def test_exact_match_non_integer_truth():
    em = ExactMatch("5/8")
    a = em.extract("the final answer is \\boxed{5/8}")
    assert a.is_ok and em.is_target(a) and em.project(a) == "5/8"
    em2 = ExactMatch("0532")  # int-like truths canonicalize
    b = em2.extract("\\boxed{532}")
    assert em2.is_target(b) and em2.project(b) == "532"


def test_manifest_records_every_named_input():
    src = MockSource()
    ps = GeneratedPrefixSource(src, "p" * 40,
                               trace_sampler=SamplerPolicy(max_new_tokens=40), seed=11)
    res = reach_scan(source=src, prefix_source=ps, projection=ModuloProjection(8, 4),
                     plan=[DepthSpec(0.5, 2)], rollout_sampler=SamplerPolicy(max_new_tokens=16),
                     base_seed=11, stop_token_ids=[7, 9])
    m = res.manifest
    assert m["stop_token_ids"] == [7, 9]
    assert m["prefix_source_provenance"]["trace_seed"] == 11
    assert m["rollout_sampler"]["top_k"] is None
    assert m["rollout_sampler"]["repetition_penalty"] == 1.0


# ---------------------------------------------------------------------------
# v0.2.3 additions (coherence-review hardening)
# ---------------------------------------------------------------------------

def test_projection_consistency_violation_raises():
    """A projection that puts target and non-target answers in ONE bucket must
    fail loud (binding consistency rule), not silently corrupt R_T."""
    class AltSource:
        name = "alt"
        def __init__(self): self.n = 0
        def encode_prompt(self, prompt, *, system=None): return [0]
        def decode(self, ids): return "A" if list(ids) == [0] else "B"
        def sample_completion(self, input_ids, *, temperature, top_p, max_new_tokens,
                              top_k=None, repetition_penalty=1.0,
                              stop_token_ids=None, seed=None, **extras):
            self.n += 1
            return [0] if self.n % 2 == 1 else [1]

    class BadProj:
        name = "bad_one_bucket"
        def extract(self, text):
            return ExtractedAnswer(ExtractedAnswer.OK, text, text)
        def project(self, a):
            return "BUCKET"            # everything in one bucket
        def is_target(self, a):
            return a.value == "A"      # ...but target depends on value -> inconsistent

    src = AltSource()
    ps = UserPrefixSource([0], [0, 0, 0, 0])
    try:
        reach_scan(source=src, prefix_source=ps, projection=BadProj(),
                   plan=[DepthSpec(1.0, 8)], rollout_sampler=SamplerPolicy(max_new_tokens=16),
                   base_seed=0)
        assert False, "expected projection consistency violation to raise"
    except ValueError:
        pass


def test_sampler_policy_validation():
    """Malformed decode policies fail at construction, before any measurement."""
    SamplerPolicy()  # defaults are valid
    bad = (dict(temperature=-0.1), dict(top_p=0.0), dict(top_p=1.5),
           dict(top_k=0), dict(repetition_penalty=0.0), dict(max_new_tokens=0))
    for kwargs in bad:
        try:
            SamplerPolicy(**kwargs)
            assert False, f"SamplerPolicy({kwargs}) should have raised"
        except ValueError:
            pass


def test_manifest_records_resolved_committed_len_and_package_version():
    from reachscan import __version__
    src = MockSource()
    ps = GeneratedPrefixSource(src, "p" * 40,
                               trace_sampler=SamplerPolicy(max_new_tokens=40), seed=11)
    L = len(ps.reference_trace_ids())
    res = reach_scan(source=src, prefix_source=ps, projection=ModuloProjection(8, 4),
                     plan=[DepthSpec(0.5, 2), DepthSpec(0.999, 2, committed_len=L - 1)],
                     rollout_sampler=SamplerPolicy(max_new_tokens=16), base_seed=11)
    by_frac = {round(p["fraction"], 3): p for p in res.manifest["plan"]}
    # fractional row: raw override is None, resolved is the rounded count
    assert by_frac[0.5]["committed_len"] is None
    assert by_frac[0.5]["resolved_committed_len"] == round(0.5 * L)
    # override row: raw and resolved both equal the explicit count
    assert by_frac[0.999]["committed_len"] == L - 1
    assert by_frac[0.999]["resolved_committed_len"] == L - 1
    assert res.manifest["package_version"] == __version__


def test_summary_ok_answers_aliases_numeric():
    src = MockSource()
    ps = UserPrefixSource(src.encode_prompt("Q"), src.encode_prompt("a b c d"))
    res = reach_scan(source=src, prefix_source=ps, projection=ModuloProjection(8, 4),
                     plan=uniform_plan([0.0, 1.0], 16),
                     rollout_sampler=SamplerPolicy(max_new_tokens=16))
    for s in res.summaries:
        assert s.ok_answers == s.numeric


def test_source_separation_requires_same_plan():
    from reachscan import source_separation
    a = _mock_scan(532)  # plan fractions [0.0, 0.9, 1.0]
    src = MockSource(basin_value=56)
    pre = GeneratedPrefixSource(src, "p", trace_sampler=SamplerPolicy(max_new_tokens=40), seed=0)
    b = reach_scan(source=src, prefix_source=pre, projection=ExactMatch(532),
                   plan=uniform_plan([0.0, 0.5, 1.0], 128),  # different middle depth
                   rollout_sampler=SamplerPolicy(max_new_tokens=16), base_seed=0)
    try:
        source_separation(a, b)
        assert False, "expected mismatched depth plans to raise"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# v0.2.4 additions (code-review hardening)
# ---------------------------------------------------------------------------

class _EmptyProj:
    """A projection that never extracts an answer (forces zero yield)."""
    name = "empty"
    def extract(self, text):
        return ExtractedAnswer(ExtractedAnswer.NO_ANSWER, None, text)
    def project(self, a):
        raise AssertionError("project called on non-ok answer")
    def is_target(self, a):
        raise AssertionError("is_target called on non-ok answer")


def test_undefined_rate_when_zero_yield():
    """Zero valid answers => R_T undefined (NaN, rate_defined False), not 0.0."""
    import math
    src = MockSource()
    ps = UserPrefixSource(src.encode_prompt("Q"), src.encode_prompt("a b c"))
    res = reach_scan(source=src, prefix_source=ps, projection=_EmptyProj(),
                     plan=[DepthSpec(0.0, 8)],
                     rollout_sampler=SamplerPolicy(max_new_tokens=16))
    s = res.summaries[0]
    assert s.ok_answers == 0 and s.rate_defined is False
    assert math.isnan(s.target_reachability)
    assert math.isnan(s.wilson_target_low) and math.isnan(s.wilson_target_high)


def test_source_separation_rejects_undefined_rows():
    """A depth with zero valid answers must make source_separation fail loud,
    not contrast an undefined (NaN) rate into an apparent foreclosure."""
    from reachscan import source_separation
    src = MockSource()
    ps = UserPrefixSource(src.encode_prompt("Q"), src.encode_prompt("a b c"))
    bad = reach_scan(source=src, prefix_source=ps, projection=_EmptyProj(),
                     plan=uniform_plan([0.0, 1.0], 8),
                     rollout_sampler=SamplerPolicy(max_new_tokens=16))
    try:
        source_separation(bad, bad)
        assert False, "expected undefined-rate rows to raise"
    except ValueError:
        pass


def test_projection_modulus_validation_and_normalization():
    for bad in (0, -3):
        try:
            ModuloProjection(bad, target_residue=1)
            assert False, "ModuloProjection should reject modulus <= 0"
        except ValueError:
            pass
        try:
            TargetFiber(bad, 532)
            assert False, "TargetFiber should reject modulus <= 0"
        except ValueError:
            pass
    # an out-of-range residue is normalized mod k (12 % 8 == 4)
    proj = ModuloProjection(8, target_residue=12)
    a = proj.extract("the answer is \\boxed{4}")
    assert a.is_ok and proj.is_target(a)


def test_hf_source_generation_config_mocked():
    """Exercise the HuggingFace adapter's generation-config build with fake
    torch/transformers (no weights, no heavy deps): the declared policy passes
    through and a pad_token_id of 0 is preserved."""
    import sys
    import types
    captured = {}
    saved = {k: sys.modules.get(k) for k in ("torch", "transformers")}

    torch = types.ModuleType("torch")

    class _Arr(list):
        def tolist(self):
            return list(self)

    class _Tensor(list):
        @property
        def device(self):
            return "cpu"

    torch.tensor = lambda data, device=None: _Tensor(data)
    torch.ones_like = lambda x: x
    torch.manual_seed = lambda s: captured.__setitem__("seed", s)

    class _NoGrad:
        def __enter__(self):
            return self
        def __exit__(self, *exc):
            return False

    torch.no_grad = lambda: _NoGrad()

    tf = types.ModuleType("transformers")

    class _GenCfg:
        def __init__(self, **kw):
            captured.update(kw)

    class _Tok:
        pad_token_id = 0
        eos_token_id = 2
        vocab_size = 32000
        chat_template = None
        @classmethod
        def from_pretrained(cls, *a, **k):
            return cls()
        def decode(self, ids, skip_special_tokens=True):
            return "x"

    class _Model:
        device = "cpu"
        @classmethod
        def from_pretrained(cls, *a, **k):
            return cls()
        def eval(self):
            return self
        def generate(self, inp, attention_mask=None, generation_config=None):
            return [_Arr(list(inp[0]) + [10, 11, 12])]

    tf.GenerationConfig = _GenCfg
    tf.AutoTokenizer = _Tok
    tf.AutoModelForCausalLM = _Model

    try:
        sys.modules["torch"] = torch
        sys.modules["transformers"] = tf
        from reachscan.hf_source import HuggingFaceSource
        src = HuggingFaceSource("fake/model")
        new_ids = src.sample_completion([1, 2, 3], temperature=0.6, top_p=0.9,
                                        max_new_tokens=8, top_k=10,
                                        repetition_penalty=1.1, seed=42)
        assert new_ids == [10, 11, 12]
        assert captured["pad_token_id"] == 0          # valid pad id 0 preserved
        assert captured["top_k"] == 10
        assert captured["temperature"] == 0.6
        assert captured["do_sample"] is True
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


def test_field_serialization_handles_nonscalar_buckets():
    """A projection with non-JSON-scalar buckets (e.g. tuples) must not crash
    write_result — field serializes as [bucket, count] pairs with a str fallback."""
    import csv
    import json
    import tempfile
    from pathlib import Path
    from reachscan.metadata import write_result

    class TupleProj:
        name = "tuple_bucket"
        def extract(self, text):
            return ExtractedAnswer(ExtractedAnswer.OK, "x", text)
        def project(self, a):
            return (1, 2)            # legal Hashable, not a JSON scalar
        def is_target(self, a):
            return True

    src = MockSource()
    ps = UserPrefixSource(src.encode_prompt("Q"), src.encode_prompt("a b c"))
    res = reach_scan(source=src, prefix_source=ps, projection=TupleProj(),
                     plan=[DepthSpec(1.0, 4)],
                     rollout_sampler=SamplerPolicy(max_new_tokens=16))
    out = Path(tempfile.mkdtemp()) / "run"
    write_result(res, out)           # must not raise
    with open(out / "summary_by_depth.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    parsed = json.loads(rows[-1]["field"])   # valid JSON array of pairs
    assert isinstance(parsed, list) and parsed and parsed[0][1] >= 1


# v0.2.5 additions: adapter-boundary regression tests for encode_prompt. These
# would have caught the BatchEncoding bug without a GPU; the live notebook smoke
# test is a backstop, not the first line of defense.

def test_hf_encode_prompt_returns_int_ids_chat_template():
    """Regression: the chat-template path must return integer token ids, not the
    KEYS of a BatchEncoding. The bug was list(apply_chat_template(tokenize=True))
    on a dict-like return -> ['input_ids', 'attention_mask']. The fix applies the
    template as text (tokenize=False) then tokenizes and indexes ['input_ids']."""
    from reachscan.hf_source import HuggingFaceSource

    class _BatchEncoding(dict):
        """dict-like: list() yields keys; indexing ['input_ids'] yields ids."""

    class _Tok:
        chat_template = "{{ messages }}"
        def apply_chat_template(self, messages, add_generation_prompt=True, tokenize=False):
            assert tokenize is False          # must request TEXT, not tokens
            assert add_generation_prompt is True
            return "TEMPLATED:" + messages[-1]["content"]
        def __call__(self, text, add_special_tokens=True):
            assert add_special_tokens is False   # template already added them
            assert text.startswith("TEMPLATED:")
            return _BatchEncoding(input_ids=[101, 102, 103], attention_mask=[1, 1, 1])

    src = HuggingFaceSource.__new__(HuggingFaceSource)   # bypass GPU __init__
    src.chat_template = True
    src._tok = _Tok()
    ids = src.encode_prompt("hello")
    assert ids == [101, 102, 103]
    assert all(isinstance(t, int) for t in ids)          # not dict keys


def test_hf_encode_prompt_no_template_path():
    """No-template fallback tokenizes the raw prompt and DOES add special tokens."""
    from reachscan.hf_source import HuggingFaceSource

    class _Tok:
        chat_template = None                  # no template available
        def __call__(self, text, add_special_tokens=True):
            assert add_special_tokens is True
            assert text == "hello"
            return {"input_ids": [5, 6, 7]}

    src = HuggingFaceSource.__new__(HuggingFaceSource)
    src.chat_template = True                   # requested, but tokenizer has none
    src._tok = _Tok()
    assert src.encode_prompt("hello") == [5, 6, 7]


def test_hf_sample_completion_rejects_non_int_ids():
    """The runtime guard catches non-int token ids (the BatchEncoding-keys
    failure mode) before torch.tensor turns it into an opaque error."""
    from reachscan.hf_source import HuggingFaceSource

    src = HuggingFaceSource.__new__(HuggingFaceSource)
    src._torch = None                          # never reached; guard fires first
    try:
        src.sample_completion(["input_ids", "attention_mask"], temperature=0.0,
                              top_p=1.0, max_new_tokens=4)
        assert False, "expected TypeError on non-int input_ids"
    except TypeError as e:
        assert "integer token ids" in str(e)


# v0.2.6 additions: checkpoint/resume support. The key invariant is that a
# resumed depth must keep its original effective-plan depth_index, because the
# seed rule is defined over (base_seed, depth_index, rollout_index).

def test_run_depth_indices_preserves_seed_semantics():
    src = MockSource()
    ps = UserPrefixSource(src.encode_prompt("Q"), src.encode_prompt("a b c d"))
    proj = ModuloProjection(8, 4)
    plan = [DepthSpec(0.0, 3), DepthSpec(0.5, 3), DepthSpec(1.0, 3)]

    full = reach_scan(source=src, prefix_source=ps, projection=proj, plan=plan,
                      rollout_sampler=SamplerPolicy(max_new_tokens=16), base_seed=99)
    resumed = reach_scan(source=src, prefix_source=ps, projection=proj, plan=plan,
                         rollout_sampler=SamplerPolicy(max_new_tokens=16), base_seed=99,
                         run_depth_indices=[2])

    full_deep = [r.seed for r in full.receipts if r.depth_index == 2]
    resumed_deep = [r.seed for r in resumed.receipts]
    assert resumed.manifest["executed_depth_indices"] == [2]
    assert {r.depth_index for r in resumed.receipts} == {2}
    assert resumed_deep == full_deep


def test_on_depth_complete_callback_is_incremental():
    src = MockSource()
    ps = UserPrefixSource(src.encode_prompt("Q"), src.encode_prompt("a b c d"))
    calls = []

    def on_depth(result):
        calls.append((len(result.summaries), len(result.receipts)))

    reach_scan(source=src, prefix_source=ps, projection=ModuloProjection(8, 4),
               plan=[DepthSpec(0.0, 2), DepthSpec(1.0, 3)],
               rollout_sampler=SamplerPolicy(max_new_tokens=16),
               on_depth_complete=on_depth)
    assert calls == [(1, 2), (2, 5)]


def test_write_and_read_result_roundtrip_for_checkpoint():
    import tempfile
    from reachscan.metadata import read_result, write_result

    src = MockSource()
    ps = UserPrefixSource(src.encode_prompt("Q"), src.encode_prompt("a b c d"))
    res = reach_scan(source=src, prefix_source=ps, projection=ModuloProjection(8, 4),
                     plan=[DepthSpec(1.0, 4)],
                     rollout_sampler=SamplerPolicy(max_new_tokens=16),
                     run_depth_indices=[0])
    out = Path(tempfile.mkdtemp()) / "checkpoint"
    write_result(res, out)
    loaded = read_result(out)
    assert loaded.manifest["executed_depth_indices"] == [0]
    assert len(loaded.summaries) == 1
    assert len(loaded.receipts) == 4
    assert loaded.summaries[0].attempts == res.summaries[0].attempts
    assert loaded.receipts[0].seed == res.receipts[0].seed


# v0.2.8 additions: cost instrumentation (token counts, cost block, estimate,
# checkpoint-aware stitching). Tokens are deterministic; wall-clock is not, so
# the tests assert on tokens/structure, never on a specific number of seconds.

def test_receipts_record_generated_token_count():
    """Every receipt carries n_new_tokens, and cap-hit receipts generated exactly
    max_new_tokens (the mock honors max_new_tokens)."""
    src = MockSource()
    ps = UserPrefixSource(src.encode_prompt("Q"), src.encode_prompt("a b c d"))
    res = reach_scan(source=src, prefix_source=ps, projection=ModuloProjection(8, 4),
                     plan=[DepthSpec(0.0, 8), DepthSpec(1.0, 8)],
                     rollout_sampler=SamplerPolicy(max_new_tokens=16))
    assert all(isinstance(r.n_new_tokens, int) and r.n_new_tokens >= 0 for r in res.receipts)
    for r in res.receipts:
        if r.hit_token_cap:
            assert r.n_new_tokens == 16


def test_cost_block_present_and_sums_to_receipts():
    """The manifest cost block separates work (tokens) from environment (seconds);
    gen_tokens_total equals the sum of per-receipt token counts."""
    src = MockSource()
    ps = UserPrefixSource(src.encode_prompt("Q"), src.encode_prompt("a b c d"))
    res = reach_scan(source=src, prefix_source=ps, projection=ModuloProjection(8, 4),
                     plan=[DepthSpec(0.0, 6), DepthSpec(0.5, 6), DepthSpec(1.0, 6)],
                     rollout_sampler=SamplerPolicy(max_new_tokens=16))
    cost = res.manifest["cost"]
    total = sum(r.n_new_tokens for r in res.receipts)
    assert cost["work"]["gen_tokens_total"] == total
    # per-depth token tallies also sum to the total
    assert sum(cost["work"]["gen_tokens_by_depth"].values()) == total
    # environment tier exists and is non-negative; runtime is None for the mock
    assert cost["environment"]["wall_clock_s_total"] >= 0.0
    assert cost["environment"]["runtime"] is None
    assert cost["environment"]["started_utc"] and cost["environment"]["ended_utc"]


def test_estimate_cost_is_an_upper_bound_on_counts():
    from reachscan import estimate_cost
    plan = [DepthSpec(0.0, 100), DepthSpec(1.0, 40)]
    est = estimate_cost(plan, seconds_per_token=0.01, max_new_tokens=512)
    assert est["total_rollouts"] == 140               # 100 + 40, no prepend (0.0 present)
    assert est["max_gen_tokens"] == 140 * 512
    assert abs(est["upper_bound_seconds"] - 140 * 512 * 0.01) < 1e-9
    # prepend case: plan without f=0 gains the prompt-only row at plan[0].rollouts
    est2 = estimate_cost([DepthSpec(0.5, 10)], seconds_per_token=0.01, max_new_tokens=8)
    assert est2["total_rollouts"] == 20               # 10 + prepended 10


def test_stitch_results_sums_cost_across_checkpoints():
    """Checkpoint-by-depth then stitch must equal a single pass on seeds AND on
    total generated tokens (the under-reporting footgun the helper fixes)."""
    import tempfile
    from reachscan.metadata import read_result, stitch_results, write_result

    src = MockSource()
    ps = UserPrefixSource(src.encode_prompt("Q"), src.encode_prompt("a b c d"))
    proj = ModuloProjection(8, 4)
    plan = [DepthSpec(0.0, 5), DepthSpec(0.5, 5), DepthSpec(1.0, 5)]
    full = reach_scan(source=src, prefix_source=ps, projection=proj, plan=plan,
                      rollout_sampler=SamplerPolicy(max_new_tokens=16), base_seed=7)

    tmp = Path(tempfile.mkdtemp())
    parts = []
    for di in range(len(full.summaries)):
        part = reach_scan(source=src, prefix_source=ps, projection=proj, plan=plan,
                          rollout_sampler=SamplerPolicy(max_new_tokens=16), base_seed=7,
                          run_depth_indices=[di])
        write_result(part, tmp / f"d{di}")
        parts.append(read_result(tmp / f"d{di}"))

    stitched = stitch_results(parts)
    assert [r.seed for r in stitched.receipts] == [r.seed for r in full.receipts]
    assert (stitched.manifest["cost"]["work"]["gen_tokens_total"]
            == full.manifest["cost"]["work"]["gen_tokens_total"])
    assert stitched.manifest["stitched_from_checkpoints"] is True
    assert "executed_depth_indices" not in stitched.manifest


def test_read_result_tolerates_pre_0_2_8_artifacts_without_token_column():
    """Old artifacts (no n_new_tokens column) still load; the count defaults to 0."""
    import tempfile
    from reachscan.metadata import read_result, write_result

    src = MockSource()
    ps = UserPrefixSource(src.encode_prompt("Q"), src.encode_prompt("a b c d"))
    res = reach_scan(source=src, prefix_source=ps, projection=ModuloProjection(8, 4),
                     plan=[DepthSpec(1.0, 4)], rollout_sampler=SamplerPolicy(max_new_tokens=16))
    out = Path(tempfile.mkdtemp()) / "old"
    write_result(res, out)
    # strip the n_new_tokens column to simulate a pre-0.2.8 receipts file
    rc = out / "receipts.csv"
    lines = rc.read_text().splitlines()
    header = lines[0].split(",")
    drop = header.index("n_new_tokens")
    stripped = [",".join(c for i, c in enumerate(row.split(",")) if i != drop) for row in lines]
    rc.write_text("\n".join(stripped) + "\n")
    loaded = read_result(out)              # must not raise
    assert all(r.n_new_tokens == 0 for r in loaded.receipts)


def test_on_progress_fires_once_per_rollout():
    src = MockSource()
    ps = UserPrefixSource(src.encode_prompt("Q"), src.encode_prompt("a b c d"))
    seen = []
    reach_scan(source=src, prefix_source=ps, projection=ModuloProjection(8, 4),
               plan=[DepthSpec(0.0, 3), DepthSpec(1.0, 4)],
               rollout_sampler=SamplerPolicy(max_new_tokens=16),
               on_progress=lambda d: seen.append((d["depth_index"], d["rollout_index"])))
    assert len(seen) == 7                  # 3 + 4 rollouts
    assert seen[0] == (0, 0) and seen[-1] == (1, 3)


# ----------------------------------------------------------------------------
# Self-runner. KEEP THIS BLOCK AT THE END OF THE FILE: it collects only the
# tests defined ABOVE it. In v0.2.0 it sat mid-file and `python
# tests/test_engine.py` silently ran 12 of the tests while reporting success;
# pytest/CI collect by name and were unaffected. The count line below makes
# under-collection visible if this ever regresses.
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    import traceback
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except Exception:
            print(f"  FAIL  {t.__name__}")
            traceback.print_exc()
    print(f"\n{passed}/{len(tests)} passed")
    sys.exit(0 if passed == len(tests) else 1)
