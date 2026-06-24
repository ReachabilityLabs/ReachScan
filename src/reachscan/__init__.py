"""reachscan — measure the future field of a committed reasoning prefix."""
__version__ = "0.2.8"

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
