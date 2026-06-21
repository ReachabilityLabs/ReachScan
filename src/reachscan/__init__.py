"""reachscan — measure the future field of a committed reasoning prefix."""
__version__ = "0.2.2"

from .contracts import (
    ExtractedAnswer,
    PrefixSource,
    Projection,
    SamplerPolicy,
    TokenContinuationSource,
)
from .engine import DepthSpec, ReachScanResult, reach_scan, uniform_plan, derive_seed
from .projections import ExactMatch, ModuloProjection, TargetFiber
from .prefix_sources import GeneratedPrefixSource, UserPrefixSource
from .mock_source import MockSource
from .contrast import source_separation, SeparationCurve, SeparationRow
