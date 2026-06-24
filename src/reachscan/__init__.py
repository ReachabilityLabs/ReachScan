"""reachscan — measure the future field of a committed reasoning prefix."""
__version__ = "0.3.2"

from .contracts import (
    ExtractedAnswer,
    PrefixSource,
    Projection,
    SamplerPolicy,
    TokenContinuationSource,
)
from .engine import (
    DepthSpec,
    ReachScanResult,
    estimate_cost,
    reach_scan,
    uniform_plan,
    derive_seed,
)
from .metadata import read_result, stitch_results, write_result
from .projections import ExactMatch, ModuloProjection, TargetFiber
from .prefix_sources import GeneratedPrefixSource, UserPrefixSource
from .mock_source import MockSource
from .contrast import source_separation, SeparationCurve, SeparationRow
from .projection_pack import (
    ProjectionPack,
    ProjectionFixture,
    PackHash,
    hash_projection_pack,
    load_projection_pack,
    load_builtin_pack,
    builtin_pack_path,
    resolve_pack,
    load_fixtures,
    validate_fixtures,
)
from .prediction import (
    RunVerdict,
    TestVerdict,
    evaluate_prediction,
    evaluate_run,
    prediction_hash,
    rows_from_result,
    write_prediction_verdict,
)
