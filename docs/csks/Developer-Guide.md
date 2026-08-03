# CSKS Developer Guide

**Milestone**: M1.23 — CSKS Developer Experience & Semantic Query Layer

This guide explains how to build, run, test, and extend the CareerOS
Self-Knowledge System (CSKS).

## 1. Prerequisites

- Python 3.11+, the project's `pyproject.toml` dependencies, and the editable
  install used by the repository (see the project README / Project Operations
  Manual).
- A Git checkout of the repository (CSKS reads git tags for milestones).

## 2. Build the index

```bash
careeros csks index
```

Builds the full knowledge graph from source code, documentation, schemas,
configuration, and git history. Prints node/edge counts. The index metadata is
written to `.csks-index/metadata.json`.

## 3. Ask questions

```bash
careeros csks query "What is ProfileLoader?"
careeros csks query "List API endpoints."
careeros csks query "What does ArtifactGenerator depend on?"
careeros csks query "Search profile." --json
```

## 4. Search

```bash
careeros csks search profile          # grouped results across entity types
careeros csks search --type domain    # faceted search (M1.22 behavior)
```

## 5. Running the test suite

CSKS tests live in `tests/test_csks_*.py`:

```bash
python -m pytest tests/test_csks_models.py tests/test_csks_extractor.py \
  tests/test_csks_builder.py tests/test_csks_query.py \
  tests/test_csks_integration.py -v
```

The full backend suite must stay green:

```bash
python -m pytest -q
```

## 6. Code layout

| Path | Purpose |
|---|---|
| `careeros/csks/models.py` | Entity/relationship/result dataclasses (frozen M1.22) |
| `careeros/csks/extractor.py` | Source extractors (Python AST, Markdown, JSON Schema, config, git) |
| `careeros/csks/builder.py` | Builds the immutable `KnowledgeGraph` from entities |
| `careeros/csks/indexer.py` | Full-index orchestration + `.csks-index` metadata |
| `careeros/csks/query.py` | `CSKSQueryEngine` + `AnswerFormatter` |
| `careeros/csks/grammar.py` | Deterministic query grammar and intent rules (M1.23) |
| `careeros/csks/aliases.py` | Alias/canonical-name registry (M1.23) |
| `careeros/csks/search.py` | Grouped term search (M1.23) |
| `careeros/csks/rich_format.py` | Rich answer formatting + source enrichment (M1.23) |
| `careeros/csks/cli.py` | Typer sub-app (`careeros csks ...`) |
| `careeros/csks/api.py` | FastAPI router (`/csks/*`) |

## 7. How to extend CSKS

### Add an entity type alias (e.g. "module" → component)

In `careeros/csks/aliases.py`, add an entry to `ENTITY_TYPE_ALIASES`:

```python
"module": "component",
```

### Add a canonical domain alias

In `careeros/csks/aliases.py`, add an `AliasEntry` to `DOMAIN_ALIASES`:

```python
AliasEntry(
    alias="export engine",
    canonical_name="Artifact Generation",
    kind="entity",
    entity_id="domain.artifact_generation",
),
```

### Add a new intent

1. Add an `IntentRule` to `RULES` in `careeros/csks/grammar.py`.
2. Add a handler in `careeros/csks/query.py` and dispatch to it in `query()`.
3. If it is a new `query_type`, add it to `QueryType` in
   `careeros/csks/models.py`.
4. Document it in `docs/csks/Query-Language.md` and add examples.

### Add a new data flow

Add a key/step-list entry to `flow_patterns` in
`careeros/csks/query.py::_handle_data_flow_path`.

### Make a node type searchable

Add a `_TYPE_TO_GROUP` mapping in `careeros/csks/search.py` (and to the CLI
group list in `careeros/csks/cli.py`).

## 8. Determinism and safety rules

- Never add AI, embeddings, vector search, or fuzzy matching.
- Never mutate the graph at query time; the interpretation layer is read-only.
- Never re-extract sources at query time; enrichment only reads a node's own
  `source_path` file and caches the result.
- Keep answers cited: every claim must trace to a `file:line`.
- Preserve backward compatibility: existing `query_type` values, API response
  shapes, and M1.22 tests must keep passing.
