"""Mission Builder: natural-language mission to evidence-backed evaluation.

The mission package turns a business mission into a structured Mission
Contract (provider-neutral interpreter) and evaluates it against a candidate
profile using only the existing deterministic optimizer machinery.
"""

from .contract import (
    MissionContract,
    MissionContractError,
    build_contract,
    normalize_requirements,
    resolve_concepts,
)
from .evaluate import (
    MissionEvaluationResult,
    MissionStatus,
    RequirementCoverage,
    RequirementStatus,
    build_job_description,
    evaluate_mission,
    evaluate_mission_many,
    render_mission_result,
)
from .interpreter import (
    MissionInterpretationError,
    MissionInterpreter,
    TruncatedMissionResponseError,
)
from .transformation import (
    PhaseContractError,
    PhaseCountError,
    TransformationInterpretationError,
    TransformationInterpreter,
    TransformationPhase,
    TransformationPlan,
    TruncatedTransformationResponseError,
)

__all__ = [
    "MissionContract",
    "MissionContractError",
    "MissionEvaluationResult",
    "MissionInterpretationError",
    "MissionInterpreter",
    "MissionStatus",
    "PhaseContractError",
    "PhaseCountError",
    "RequirementCoverage",
    "RequirementStatus",
    "TransformationInterpretationError",
    "TransformationInterpreter",
    "TransformationPhase",
    "TransformationPlan",
    "TruncatedMissionResponseError",
    "TruncatedTransformationResponseError",
    "build_contract",
    "build_job_description",
    "evaluate_mission",
    "evaluate_mission_many",
    "normalize_requirements",
    "render_mission_result",
    "resolve_concepts",
]
