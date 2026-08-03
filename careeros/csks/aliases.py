"""Deterministic alias registry for CSKS entity resolution (M1.23).

Maps user-facing names and aliases to graph entities. All lookups are exact,
case-insensitive, and punctuation-folded. This is the interpretation layer's
source of truth for "what does the user mean" — no fuzzy matching.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AliasEntry:
    """A single registry entry mapping an alias to a deterministic target."""

    alias: str
    canonical_name: str
    kind: str  # "entity" | "cluster" | "absent"
    entity_id: str | None = None
    module_prefix: str | None = None
    absent_hint: str = ""


ENTITY_TYPE_ALIASES: dict[str, str] = {
    "api": "api_endpoint",
    "endpoint": "api_endpoint",
    "endpoints": "api_endpoint",
    "rest endpoint": "api_endpoint",
    "rest endpoints": "api_endpoint",
    "cli": "cli_command",
    "command": "cli_command",
    "commands": "cli_command",
    "cli command": "cli_command",
    "cli commands": "cli_command",
    "rule": "rule",
    "rules": "rule",
    "reasoning rule": "rule",
    "reasoning rules": "rule",
    "generator": "generator",
    "generators": "generator",
    "schema": "schema",
    "schemas": "schema",
    "test": "test",
    "tests": "test",
    "adr": "adr",
    "adrs": "adr",
    "milestone": "milestone",
    "milestones": "milestone",
    "domain": "domain",
    "domains": "domain",
    "component": "component",
    "components": "component",
    "config": "configuration",
    "configuration": "configuration",
    "configurations": "configuration",
    "principle": "principle",
    "principles": "principle",
}

DOMAIN_ALIASES: tuple[AliasEntry, ...] = (
    AliasEntry(
        alias="profile management",
        canonical_name="Profile Management",
        kind="entity",
        entity_id="domain.profile_management",
    ),
    AliasEntry(
        alias="knowledge layer",
        canonical_name="Knowledge Layer",
        kind="entity",
        entity_id="domain.knowledge_graph",
    ),
    AliasEntry(
        alias="knowledge graph",
        canonical_name="Knowledge Graph",
        kind="entity",
        entity_id="domain.knowledge_graph",
    ),
    AliasEntry(
        alias="reasoning engine",
        canonical_name="Reasoning Engine",
        kind="entity",
        entity_id="domain.reasoning",
    ),
    AliasEntry(
        alias="reasoning",
        canonical_name="Reasoning",
        kind="entity",
        entity_id="domain.reasoning",
    ),
    AliasEntry(
        alias="artifact generation",
        canonical_name="Artifact Generation",
        kind="entity",
        entity_id="domain.artifact_generation",
    ),
    AliasEntry(
        alias="artifact generator",
        canonical_name="Artifact Generation",
        kind="entity",
        entity_id="domain.artifact_generation",
    ),
    AliasEntry(
        alias="interview intelligence",
        canonical_name="Interview Intelligence",
        kind="cluster",
        module_prefix="careeros.interview",
        absent_hint="No Interview Intelligence domain node exists in the current graph; "
        "resolved to interview-simulation components.",
    ),
    AliasEntry(
        alias="cv optimization",
        canonical_name="CV Optimization",
        kind="entity",
        entity_id="domain.cv_optimization",
    ),
    AliasEntry(
        alias="schema foundation",
        canonical_name="Schema Foundation",
        kind="entity",
        entity_id="domain.schema_foundation",
    ),
    AliasEntry(
        alias="delivery interfaces",
        canonical_name="Delivery Interfaces",
        kind="entity",
        entity_id="domain.delivery_interfaces",
    ),
    AliasEntry(
        alias="knowledge ingestion",
        canonical_name="Acquisition (Knowledge Ingestion)",
        kind="entity",
        entity_id="domain.acquisition_knowledge_ingestion",
    ),
)

ALL_ALIASES: tuple[AliasEntry, ...] = DOMAIN_ALIASES


def _fold(value: str) -> str:
    """Fold an alias into the registry lookup key."""
    return " ".join(value.lower().replace("-", " ").replace("_", " ").split())


_REGISTRY: dict[str, AliasEntry] = {}
for _entry in ALL_ALIASES:
    _REGISTRY[_fold(_entry.alias)] = _entry
    _REGISTRY[_fold(_entry.canonical_name)] = _entry


def resolve_alias(value: str) -> AliasEntry | None:
    """Resolve a raw alias/canonical name to an AliasEntry, or None."""
    return _REGISTRY.get(_fold(value))
