# ADR 008: CareerOS Self-Knowledge System (CSKS) Foundation

## Status

Accepted

## Context

CareerOS has accumulated substantial architectural knowledge across 74 documentation files, 6 ADRs, 23 reasoning rules, 20 REST endpoints, 13 CLI commands, 18 JSON schemas, 3 milestone specifications, and a growing codebase spanning 8 Core domains. This knowledge is currently fragmented across:

- Architecture documents (`docs/architecture/`)
- Platform Beta specifications (`docs/platform-beta/`)
- ADRs (`docs/adr/`, `docs/platform-beta/ADR-*`)
- Source code (`careeros/`, `api/`, `careeros_cli/`, `frontend/src/`)
- JSON Schemas (`schemas/`)
- Tests (`tests/`)
- Configuration files
- Git history (tags, commits)

Developers and AI agents currently lack a single, queryable interface to answer structural questions about CareerOS such as:
- "What domains depend on Profile Management?"
- "What are the inputs to the TotalYearsExperienceRule?"
- "What is the data flow for artifact generation?"
- "What is the status of M1.21?"
- "What breaks if I change ProfileLoader?"

Current approaches (grep, manual doc reading, tribal knowledge) are slow, error-prone, and don't scale.

## Decision

Implement the **CareerOS Self-Knowledge System (CSKS)** as a **Core domain** (`careeros/csks/`) that:

1. **Extracts** structured knowledge from all CareerOS sources (code, docs, schemas, configs, tests, git)
2. **Populates** the existing `careeros.knowledge.KnowledgeGraph` with CSKS entities as `GraphNode`/`GraphEdge` instances
3. **Queries** the graph via a traversal + filter engine
4. **Exposes** answers via CLI (`careeros csks query`) and REST API (`GET /csks/query`)

### Core Design Principles

| Principle | Application |
|---|---|
| **Deterministic** | No LLM in the critical path. Same sources → same graph → same answers. |
| **Reuses Existing Graph Engine** | CSKS uses `careeros.knowledge.KnowledgeGraph` directly — no parallel graph. |
| **Citations mandatory** | Every answer includes `file:line` source references. |
| **Incremental** | Git-aware indexer updates only changed entities (M1.23). |
| **Core domain** | CSKS is part of `careeros/` Core, not a Module. No LLM dependencies. |
| **Reuse over rebuild** | Reuses `KnowledgeGraph`, `RuleRegistry`, `SchemaLoader`, topological sort patterns. |

### CSKS Knowledge Model

**Entities** (12 types): `Domain`, `ArchitectureComponent`, `APIEndpoint`, `CLICommand`, `Rule`, `Generator`, `Schema`, `Test`, `ADR`, `Milestone`, `Configuration`, `Principle`, `DataFlow`, `Dependency`

**Relationships** (12 types): `contains`, `depends_on`, `produces`, `consumes`, `implements`, `validates_against`, `flows_to`, `references`, `specifies`, `tags`, `configures`

**Metadata**: `id`, `source_path`, `version`, `status`, `owner_domain`, `tags`, `last_updated`, `confidence`

### Extractor Architecture

CSKS defines a `KnowledgeExtractor` protocol for source-specific extraction:

```python
from typing import Protocol, Iterable
from careeros.csks.models import ExtractedEntity, ExtractedRelationship

class KnowledgeExtractor(Protocol):
    """Protocol for extracting structured knowledge from a source."""
    
    def can_extract(self, source_path: str) -> bool:
        """Return True if this extractor can handle the given source."""
        ...
    
    def extract(self, source_path: str) -> Iterable[ExtractedEntity]:
        """Extract entities from the source."""
        ...
    
    def extract_relationships(self, source_path: str) -> Iterable[ExtractedRelationship]:
        """Extract relationships from the source."""
        ...
```

**Concrete Extractors** (M1.22):
- `PythonASTExtractor` — AST walker for `.py` files (classes, functions, imports, decorators)
- `MarkdownExtractor` — ADR frontmatter, tables, Mermaid diagrams
- `JSONSchemaExtractor` — `.schema.json` files
- `YAMLTOMLConfigExtractor` — `pyproject.toml`, `.env.example`, `vite.config.ts`
- `GitTagExtractor` — milestone/release tags from git history

### Graph Engine Reuse

**CSKS does not create a parallel graph implementation.** Instead:

| Reused Component | How CSKS Uses It |
|---|---|
| `careeros.knowledge.GraphNode` | Stores CSKS entities (`type` = CSKS entity type, `properties` = entity fields) |
| `careeros.knowledge.GraphEdge` | Stores CSKS relationships |
| `careeros.knowledge.KnowledgeGraph` | Directly used as the graph engine; no subclassing |
| `careeros.knowledge.KnowledgeGraphBuilder` | Pattern reused; CSKS has `CSKSKnowledgeGraphBuilder` |
| `careeros.knowledge.KnowledgeGraph` query methods | Extended with CSKS-specific traversals via composition |

The existing `KnowledgeGraph` class is used directly. CSKS entities are stored as `GraphNode` instances with `type` set to CSKS entity types (e.g., `"domain"`, `"component"`, `"rule"`) and `properties` containing entity-specific fields. CSKS relationships are stored as `GraphEdge` with `type` set to CSKS relationship types (e.g., `"depends_on"`, `"contains"`).

### Interfaces

| Interface | Description |
|---|---|
| **CLI** | `careeros csks query "what depends on Profile Management?"` |
| **REST API** | `GET /csks/query?q=...` → JSON with answer, citations, confidence |
| **Answer format** | `{answer, citations[], confidence=1.0, entities_found, query_time_ms}` |

### Phased Implementation

| Milestone | Scope |
|---|---|
| **M1.22** | Spec, ADR, Knowledge Model, Extractor (code+docs), Builder, Query Engine, CLI, API, Tests (full index on startup) |
| **M1.23** | Incremental Indexing, CI Integration, Auto-index on commit |
| **M1.24** | Consumers: Doc generator, Architecture compliance checker, Onboarding assistant |
| **M1.25** | Optional LLM Formatting Layer (natural language synthesis on deterministic results) |

## Architecture Compliance

| Guardrail | Compliance |
|---|---|
| Canonical Profile as single source of truth | ✅ CSKS is meta-knowledge; does not touch career data |
| Frontend = Presentation only | ✅ M1.22 has no frontend |
| API = Transport only | ✅ `/csks/query` delegates to CSKS domain |
| Domain owns business logic | ✅ CSKS is a Core domain |
| Dependency flow: UI → API → Domain | ✅ CLI/API → CSKS domain → Core services |
| No lateral bypassing | ✅ CSKS reads sources directly |
| Deterministic reasoning | ✅ No LLM in M1.22; pure graph traversal |
| Provider agnostic | ✅ No AI provider dependencies |
| **No parallel graph** | ✅ Reuses `careeros.knowledge.KnowledgeGraph` directly |

## Consequences

**Positive**:
- CareerOS becomes self-documenting and self-navigable
- AI agents (ChatGPT, Copilot, OpenCode) can accurately answer CareerOS questions
- Architecture compliance becomes verifiable via CSKS queries
- New developer onboarding accelerated via `csks query`
- Impact analysis for changes becomes automated
- **Zero graph infrastructure duplication** — leverages existing tested infrastructure

**Negative**:
- Additional Core domain to maintain
- Extraction logic must evolve with codebase patterns
- Index freshness requires CI integration (M1.23)
- Initial extraction coverage gaps require iterative improvement

## Alternatives Considered

| Alternative | Rejected Because |
|---|---|
| Pure RAG (LLM over docs) | Contradicts "Reasoning Before Generation"; hallucination risk; non-deterministic |
| External knowledge base (Notion, Confluence) | External dependency; not version-controlled with code |
| Do nothing (grep/docs) | Doesn't scale; error-prone; no structured answers |
| External tool (Sourcegraph, etc.) | Vendor lock-in; not tailored to CareerOS domain model |
| Parallel graph implementation | Duplicates tested infrastructure; adds maintenance burden |

## Relationships

- **Builds on**: ADR-004 (Core Boundaries), ADR-006 (AI Provider Abstraction), ADR-007 (Session Lifecycle patterns)
- **Enables**: Future architecture compliance CI gates, automated documentation generation, AI agent integration
- **Precedes**: M1.23 (Incremental Indexing), M1.24 (Consumers), M1.25 (LLM Formatting)

## Implementation Notes

- CSKS is a **Core domain** under `careeros/csks/` — not a Module
- Reuses `careeros/knowledge/` (GraphNode, GraphEdge, KnowledgeGraph, builder)
- Reuses `careeros/reasoning/registry.py` (topological sort for dependency ordering)
- Reuses `careeros/schema_loader.py` (schema discovery patterns)
- No LLM in M1.22; optional formatting layer in M1.25
- Incremental indexing deferred to M1.23 (git diff + partial rebuild)
- **CSKS models** (`careeros/csks/models.py`) define type-safe dataclasses for extraction output; these map to `GraphNode.properties` / `GraphEdge.properties` at build time

## Decision Log

| Date | Decision |
|---|---|
| 2026-08-02 | CSKS approved as Core domain; M1.22 authorized for implementation |
| 2026-08-02 | Refined: CSKS reuses `careeros.knowledge.KnowledgeGraph` directly; no parallel graph; `KnowledgeExtractor` protocol defined |

---

*This ADR is immutable once accepted. Amendments require a new ADR.*