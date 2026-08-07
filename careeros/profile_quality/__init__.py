"""Profile Quality Engine (Core) — M1.24.1.

Deterministic, profile-centric evaluation facade that composes the existing
Reasoning Engine, Resolution Engine, and the eight pure dimension calculators
into a ``ProfileQualityReport`` with a citable 0-100 Resume Health score.
"""

from .engine import ProfileQualityEngine, run_profile_quality
from .report import (
    PROFILE_QUALITY_ENGINE_VERSION,
    Citation,
    DimensionScore,
    Finding,
    HealthDimension,
    ProfileQualityReport,
    RULE_ID_TO_DIMENSION,
    resolution_type_for_rule,
)
from .dimensions import (
    DIMENSION_CALCULATORS,
    DIMENSION_LABELS,
    DIMENSION_WEIGHTS,
    HEALTH_DIMENSIONS,
    health_dimensions,
)
from .unified import (
    SOURCE_OPTIMIZATION,
    SOURCE_PROFILE_QUALITY,
    UnifiedRecommendation,
    filter_and_sort_recommendations,
    to_unified_recommendations,
    unified_recommendation_sort_key,
)

__all__ = [
    "Citation",
    "DimensionScore",
    "DIMENSION_CALCULATORS",
    "DIMENSION_LABELS",
    "DIMENSION_WEIGHTS",
    "Finding",
    "HealthDimension",
    "HEALTH_DIMENSIONS",
    "PROFILE_QUALITY_ENGINE_VERSION",
    "ProfileQualityEngine",
    "ProfileQualityReport",
    "RULE_ID_TO_DIMENSION",
    "SOURCE_OPTIMIZATION",
    "SOURCE_PROFILE_QUALITY",
    "UnifiedRecommendation",
    "filter_and_sort_recommendations",
    "health_dimensions",
    "resolution_type_for_rule",
    "run_profile_quality",
    "to_unified_recommendations",
    "unified_recommendation_sort_key",
]
