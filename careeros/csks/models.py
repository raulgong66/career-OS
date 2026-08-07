from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional
from uuid import UUID, uuid4


@dataclass(frozen=True)
class ExtractedEntity:
    """An entity extracted from a source file by a KnowledgeExtractor."""

    entity_type: str
    id: str
    properties: dict[str, Any]
    source_path: str
    line_start: int
    line_end: int
    confidence: float = 1.0


@dataclass(frozen=True)
class ExtractedRelationship:
    """A relationship extracted from a source file."""

    from_id: str
    to_id: str
    relationship_type: str
    properties: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0


@dataclass(frozen=True)
class Citation:
    """A source citation for an answer."""

    file: str
    line_start: int
    line_end: int
    text: str
    entity_id: str


@dataclass(frozen=True)
class StructuredQueryResult:
    """Structured result from the query engine before formatting."""

    answer: str
    citations: tuple[Citation, ...]
    matched_entities: tuple[str, ...]
    traversal_path: tuple[str, ...]
    confidence: float
    entities_found: int
    query_time_ms: int
    query_type: str


@dataclass(frozen=True)
class CSKSAnswer:
    """Final formatted answer for CLI/API output."""

    answer: str
    citations: tuple[Citation, ...]
    confidence: float
    entities_found: int
    query_time_ms: int
    query_type: str


QueryType = Literal[
    "entity_lookup",
    "type_filter",
    "dependency_traversal",
    "data_flow_path",
    "capability_check",
    "status_check",
    "impact_analysis",
    "unknown",
    "reverse_dependency",
    "search",
    "profile_quality_check",
    "improvement_queue",
    "stale_artifacts",
]


ENTITY_TYPES = (
    "domain",
    "component",
    "api_endpoint",
    "cli_command",
    "rule",
    "generator",
    "schema",
    "test",
    "adr",
    "milestone",
    "configuration",
    "principle",
    "dataflow",
    "dependency",
    "document",
    "mermaid_edge",
    "table_row",
    "release",
    "tag",
)

RELATIONSHIP_TYPES = (
    "contains",
    "depends_on",
    "produces",
    "consumes",
    "implements",
    "validates_against",
    "flows_to",
    "references",
    "specifies",
    "tags",
    "configures",
)


def make_entity_id(entity_type: str, name: str) -> str:
    """Generate a deterministic entity ID from type and name."""
    return f"{entity_type}.{name.lower().replace(' ', '_').replace('-', '_')}"


def make_relationship_id(from_id: str, to_id: str, rel_type: str) -> str:
    """Generate a deterministic relationship ID."""
    return f"{from_id}--{rel_type}--{to_id}"


def is_valid_entity_type(entity_type: str) -> bool:
    return entity_type in ENTITY_TYPES


def is_valid_relationship_type(rel_type: str) -> bool:
    return rel_type in RELATIONSHIP_TYPES