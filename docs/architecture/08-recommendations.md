# 08 — Recommendations

This document separates **observations** (what exists) from **recommendations** (what should be done). Recommendations are based only on the current implementation, not on hypothetical future features.

---

## Short-Term Improvements (Single Sprint, <1 Week)

### High Priority

| # | Recommendation | Rationale | Evidence |
|---|---|---|---|
| 1 | Add `httpx` to `pyproject.toml` dependencies | Prevents runtime failure for acquisition pipeline users | `careeros/acquisition/llm_extractor.py` imports `httpx` but `pyproject.toml` does not declare it (see technical debt #7) |
| 2 | Extract shared rendering utilities from `MarkdownCVGenerator` | `DocxCVGenerator` and `MarkdownCoverLetterGenerator` both depend on `MarkdownCVGenerator`'s private helpers; a shared `utils/rendering.py` module would eliminate this implicit coupling | `careeros/generators/markdown_cover_letter.py` imports `MarkdownCVGenerator` for `_person_name()`; `careeros/generators/docx_cv.py` composes it (see debt #3) |

### Medium Priority

| # | Recommendation | Rationale | Evidence |
|---|---|---|---|
| 3 | Define a `Pipeline` or `Stage` protocol | `generate_artifact()` and `AcquisitionPipeline.run()` hard-code sequential steps; a composable pipeline abstraction would allow middleware (logging, caching, metrics) without modifying existing functions | `careeros/pipelines.py` and `careeros/acquisition/pipeline.py` (see debt #4) |

### Low Priority

| # | Recommendation | Rationale | Evidence |
|---|---|---|---|
| 4 | Remove legacy `POST /create/{entity}` endpoint | Overlaps with `POST /entities/{entity}` and returns a different status code (200 vs 201), creating API inconsistency | `api/main.py` lines for both endpoints (see debt #9) |

---

## Long-Term Improvements (Multiple Sprints, 1-4 Weeks)

### High Priority

| # | Recommendation | Rationale | Evidence |
|---|---|---|---|
| 5 | Define an abstract `Graph` protocol for the knowledge layer | `ReasoningEngine`, `RuleContext`, and all 14 rules depend on the concrete `KnowledgeGraph` class. An abstract protocol would allow the reasoning package to be extracted independently, enable alternative graph backends (RDF, remote, mock), and break the circular-ish dependency between reasoning and knowledge | `careeros/reasoning/engine.py:29`, `careeros/reasoning/models.py:32` (see debt #1) |
| 6 | Consolidate domain models across layers | `PersonData` (acquisition), `ExportSource` (export), and `EntityRecord` (core) represent overlapping concepts. A single shared domain model layer (or at least consistent interfaces) would reduce conversion code and field mismatch risk | `careeros/acquisition/person_data.py`, `careeros/export_contract.py`, `careeros/models.py` (see debt #2) |

### Medium Priority

| # | Recommendation | Rationale | Evidence |
|---|---|---|---|
| 7 | Establish a single profile identity authority | Profile ID is resolved independently in the reasoning engine, export contract builder, and acquisition pipeline. A standard identifier resolution strategy would ensure consistency across all stages | `ReasoningEngine._resolve_profile_id()` defaults to `"unknown"`; acquisition generates IDs independently (see debt #8) |
| 8 | Add entry-point-based generator auto-discovery | The `default_generator_registry()` function hard-codes all generators. Supporting Python entry points or a registration decorator would let third-party packages add generators without modifying `careeros` code | `careeros/generators/registry.py` (see debt #5) |

### Low Priority

| # | Recommendation | Rationale | Evidence |
|---|---|---|---|
| 9 | Variable confidence scoring for reasoning rules | All 14 rules currently return `confidence=1.0`. Real confidence scoring (e.g., based on data completeness, recency, evidence strength) would make the reasoning output more informative | All rule implementations in `careeros/reasoning/rules/*.py` return `confidence=1.0` |
| 10 | Asynchronous graph queries | `KnowledgeGraph` query methods are synchronous and traverse in-memory data. A concurrent or lazy query interface would prepare for larger profiles or remote data sources | `careeros/knowledge/models.py` — all query methods are synchronous list/dict operations |

---

## Observations Without Recommendations

These are architectural observations where the current implementation is acceptable for the current scale and no immediate action is warranted:

| Observation | Context |
|---|---|
| Flat repository layout with multiple top-level packages prevents `pip install -e .` | The project works with PYTHONPATH set; restructuring to a `src/` layout would be disruptive |
| Filesystem-based repository with no indexing | Acceptable for single-user or small-scale use; a database-backed implementation would be premature |
| Synchronous single-threaded pipeline | 14 rules complete in <100ms; asynchronous execution adds complexity without benefit at current scale |
| All runtime dependencies in a single `pyproject.toml` | Both CLI and API have the same dependency set; extracting shared libraries could reduce install size but is not needed |
| No explicit interface for the rule execution context | `RuleContext` is a frozen dataclass, which is sufficient for current use; formalizing the interface would add ceremony without benefit |
