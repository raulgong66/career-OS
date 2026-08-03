# CSKS Architecture

**Milestone**: M1.23 — CSKS Developer Experience & Semantic Query Layer

This document describes the architecture of the CareerOS Self-Knowledge System
(CSKS) after M1.23. It explains the layered design, the frozen M1.22 core, and the
new interpretation/presentation layer.

## 1. Overview

CSKS answers deterministic questions about the CareerOS codebase: components,
domains, ADRs, milestones, reasoning rules, schemas, API endpoints, CLI commands,
data flows, and dependency/impact analysis.

```
 ┌────────────────────────────────────────────────────────────────┐
 │ Presentation / Interpretation layer (M1.23, all read-only)     │
 │                                                                │
 │   grammar.py      deterministic query grammar + intent rules   │
 │   aliases.py      canonical-name / alias registry              │
 │   search.py       grouped term search                          │
 │   rich_format.py  sectioned, cited answer formatting           │
 │                  (docstring/table enrichment, fallback safe)   │
 └───────────────────────────┬────────────────────────────────────┘
                             │
 ┌───────────────────────────▼────────────────────────────────────┐
 │ Query engine (M1.22, extended M1.23)                           │
 │   CSKSQueryEngine  traversal, filtering, path finding,         │
 │                    entity resolution, intent handlers          │
 └───────────────────────────┬────────────────────────────────────┘
                             │
 ┌───────────────────────────▼────────────────────────────────────┐
 │ Frozen M1.22 core (NOT replaced)                               │
 │   KnowledgeGraph / GraphNode / GraphEdge  (careeros.knowledge) │
 │   extractors (AST, Markdown, JSON Schema, config, git)         │
 │   CSKSKnowledgeGraphBuilder  entities -> immutable graph       │
 │   CSKSIndexer  full index + .csks-index/metadata.json          │
 │   entity/relationship model (careeros.csks.models)             │
 └────────────────────────────────────────────────────────────────┘
```

## 2. Layering rules

- **Frozen (may be extended, never replaced):** `careeros.knowledge`
  (`KnowledgeGraph`, `GraphNode`, `GraphEdge`), extractor architecture, builder
  architecture, index storage (`.csks-index`), existing REST endpoints, and the
  entity/relationship model.
- **M1.23 additions** live in `careeros/csks/` and only *read* the graph. They do not
  mutate it, do not re-extract sources, and do not persist state.
- **Determinism:** same sources → same graph → same answers. No AI, no embeddings,
  no vector search, no fuzzy matching anywhere.

## 3. Modules

### 3.1 `careeros/csks/grammar.py`

An ordered, first-match-wins rule table. Each `IntentRule` has trigger regexes, an
optional deterministic target extractor, and an optional guard. `classify(question)`
returns a `ClassifiedIntent(query_type, target, params)`; `suggest(question)` returns
deterministic "did you mean" suggestions.

Intent categories: component lookup, domain lookup, listing, dependency analysis,
reverse dependency, impact analysis, data flow, search, capability check, status
check, unknown.

### 3.2 `careeros/csks/aliases.py`

A versioned registry mapping user-facing aliases to graph entities:

- **Entity-type aliases** (e.g. `api` → `api_endpoint`, `rule` → `rule`).
- **Domain canonical names** (`Profile Management`, `Knowledge Layer`,
  `Reasoning Engine`, `Artifact Generation`, `Interview Intelligence`, ...).
- Resolution kinds: `entity` (direct graph id), `cluster` (deterministic module
  prefix rule, e.g. Interview Intelligence → `careeros.interview*` components),
  `absent` (honest no-match with hints).

### 3.3 `careeros/csks/search.py`

`grouped_search(graph, term, per_group, limit)` returns results grouped by entity
type (Domains, Components, APIs, Schemas, Rules, Generators, Tests, Milestones,
ADRs, CLI commands, Configurations, Documents). Matching is substring/prefix/exact
over node id and label. Used by the CLI `search` command and the `search` query
intent.

### 3.4 `careeros/csks/rich_format.py`

`RichFormatter` renders Components, Rules, Generators, Domains, ADRs, Milestones,
and Schemas as sectioned, cited text. Purpose text is enriched deterministically
from the node's own source file (Python docstring via `ast`, domain-map table row,
ADR Context/Summary paragraph, schema description). Enrichment is cached, safe on
missing/unparseable files, and falls back to structured facts.

### 3.5 `careeros/csks/query.py`

`CSKSQueryEngine` was extended (not replaced):

- `query()` dispatches on the grammar's intent; `_classify_query` delegates to the
  grammar (kept for compatibility).
- New handlers: `_handle_reverse_dependency` and `_handle_search`.
- `_handle_data_flow_path` now accepts the classified flow topic and covers
  `artifact generation`, `cv`, `interview preparation`, `acquisition`, `reasoning`.
- `_resolve_target` gained milestone tag-prefix resolution; `_resolve_token`
  consults the alias registry and handles underscore-prefixed names.
- `_handle_unknown` now produces "I could not classify your query." plus
  deterministic suggestions.
- The engine takes an optional `repo_root` so source enrichment resolves paths
  correctly regardless of the current working directory.

## 4. QueryType values

The `QueryType` literal is extended additively with `reverse_dependency` and
`search`. Existing values (`entity_lookup`, `type_filter`, `dependency_traversal`,
`data_flow_path`, `capability_check`, `status_check`, `impact_analysis`,
`unknown`) are unchanged.

## 5. Data flow

1. User asks a question via CLI (`careeros csks query "..."`) or API
   (`GET /csks/query?q=...`).
2. `grammar.classify` maps the question to an intent.
3. `CSKSQueryEngine` dispatches to the handler, which resolves entities
   (`_resolve_target` / `_resolve_token` + alias registry) and traverses the graph.
4. Rich answers are assembled by `RichFormatter` (entities) or the search/flow
   handlers, each with `file:line` citations.
5. `AnswerFormatter` renders the result for CLI text or JSON.

## 6. Extensibility

- New intent: add an `IntentRule` to the grammar and a handler in the query engine.
- New alias: add an `AliasEntry` to the registry.
- New searchable type: add a `_TYPE_TO_GROUP` mapping.
- New flow: add a key to the flow table in `_handle_data_flow_path`.

## References

- `docs/platform-beta/M1.23-CSKS-Developer-Experience.md` — design document.
- `docs/data-model/CSKS-Knowledge-Model.md` — entity/relationship catalog.
- `docs/architecture/02-domain-map.md` — canonical domain map.
- `careeros/csks/*.py` — implementation.
