"""CareerOS Self-Knowledge System (CSKS) — M1.22.

The CSKS builds a deterministic knowledge graph of the CareerOS repository
itself, reusing the existing ``careeros.knowledge`` graph engine. It answers
questions about domains, components, rules, schemas, ADRs, milestones and
configuration via a structured query engine.
"""

from __future__ import annotations

from .models import (
    CSKSAnswer,
    Citation,
    ExtractedEntity,
    ExtractedRelationship,
    ENTITY_TYPES,
    RELATIONSHIP_TYPES,
    StructuredQueryResult,
    make_entity_id,
    make_relationship_id,
)
from .extractor import (
    BaseExtractor,
    GitTagExtractor,
    JSONSchemaExtractor,
    KnowledgeExtractor,
    MarkdownExtractor,
    PythonASTExtractor,
    YAMLTOMLConfigExtractor,
    get_all_extractors,
)
from .builder import CSKSKnowledgeGraphBuilder, CSKSExtractorOrchestrator
from .query import CSKSQueryEngine, AnswerFormatter, QueryResult
from .indexer import CSKSIndexer, IndexMetadata

__all__ = [
    "CSKSAnswer",
    "Citation",
    "ExtractedEntity",
    "ExtractedRelationship",
    "StructuredQueryResult",
    "ENTITY_TYPES",
    "RELATIONSHIP_TYPES",
    "make_entity_id",
    "make_relationship_id",
    "KnowledgeExtractor",
    "BaseExtractor",
    "PythonASTExtractor",
    "MarkdownExtractor",
    "JSONSchemaExtractor",
    "YAMLTOMLConfigExtractor",
    "GitTagExtractor",
    "get_all_extractors",
    "CSKSKnowledgeGraphBuilder",
    "CSKSExtractorOrchestrator",
    "CSKSQueryEngine",
    "AnswerFormatter",
    "QueryResult",
    "CSKSIndexer",
    "IndexMetadata",
]
