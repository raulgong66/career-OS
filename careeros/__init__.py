"""Core library for CareerOS."""

from .exceptions import (
    CareerOSException,
    EntityNotFoundError,
    RepositoryError,
    SchemaLoadError,
    ValidationError,
)
from .models import EntityRecord, ValidationResult
from .export_contract import ExportContract, ExportContractBuilder, ExportSource
from .evidence_selector import EvidenceSelector
from .generators import (
    DocxCVGenerator,
    GeneratorRegistry,
    MarkdownCoverLetterGenerator,
    MarkdownCVGenerator,
    default_generator_registry,
)
from .profile_loader import ProfileLoader
from .pipelines import generate_artifact, generate_markdown_cv, generate_tailored_artifact
from .repository import FileSystemRepository
from .schema_loader import SchemaLoader
from .validator import EntityValidator
from .optimizer import CVOptimizer, OptimizationResult, OptimizationStatus, OptimizationSummary, Recommendation, RequirementConcept, CONCEPT_TAXONOMY
from .docx_renderer import CVDocumentRenderer
from .recommendation_applier import RecommendationApplier

from .acquisition import (
    AcquisitionPipeline,
    CanonicalProfileBuilder,
    DocumentReader,
    LLMExtractor,
    OpenAILLMExtractor,
    PersonData,
    TextExtractor,
    YamlWriter,
)

__all__ = [
    "CareerOSException",
    "EntityNotFoundError",
    "EntityRecord",
    "EntityValidator",
    "ExportContract",
    "ExportContractBuilder",
    "ExportSource",
    "EvidenceSelector",
    "FileSystemRepository",
    "GeneratorRegistry",
    "default_generator_registry",
    "DocxCVGenerator",
    "generate_artifact",
    "generate_markdown_cv",
    "generate_tailored_artifact",
    "MarkdownCoverLetterGenerator",
    "MarkdownCVGenerator",
    "ProfileLoader",
    "RepositoryError",
    "SchemaLoader",
    "SchemaLoadError",
    "ValidationError",
    "ValidationResult",
    "CVOptimizer",
    "OptimizationResult",
    "OptimizationStatus",
    "OptimizationSummary",
    "Recommendation",
    "RequirementConcept",
    "CONCEPT_TAXONOMY",
    "CVDocumentRenderer",
    "RecommendationApplier",
    "AcquisitionPipeline",
    "CanonicalProfileBuilder",
    "DocumentReader",
    "LLMExtractor",
    "OpenAILLMExtractor",
    "PersonData",
    "TextExtractor",
    "YamlWriter",
]
