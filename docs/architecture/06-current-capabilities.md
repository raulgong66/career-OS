# 06 — Current Capabilities

## Capability Inventory

### Canonical Profile

| Capability | Status | Details |
|---|---|---|
| Schema definition | Implemented | 18 JSON Schema files (Draft 2020-12) |
| Schema discovery | Implemented | `SchemaLoader` auto-discovers all `*.schema.json` files |
| Schema validation | Implemented | `EntityValidator` using `jsonschema` + `referencing` |
| Profile YAML loading | Implemented | `ProfileLoader` with optional validation |
| Profile JSON loading | Implemented | `ProfileLoader` supports both YAML and JSON |
| Entity CRUD | Implemented | `FileSystemRepository` (save, get, update, delete, search) |
| Profile versioning | Partial | `profileVersion` field exists but no migration path |

### Knowledge Graph

| Capability | Status | Details |
|---|---|---|
| Graph construction | Implemented | `KnowledgeGraphBuilder.build(profile)` |
| 5 node types | Implemented | person, experience, skill, education, organization |
| 7 edge types | Implemented | 7 directed relationships (see domain map) |
| Bidirectional skill-experience traversal | Implemented | `USES_SKILL` and `USED_IN_EXPERIENCE` |
| Graph queries | Implemented | `skills()`, `experiences()`, `skills_used_by()`, `organizations_for_skill()`, etc. |
| Immutability | Implemented | Graph is read-only after construction |
| Determinism | Implemented | Same profile → same graph always |

### Reasoning

| Capability | Status | Details |
|---|---|---|
| Rule registration | Implemented | `RuleRegistry` with dependency validation |
| Topological execution | Implemented | Kahn's algorithm for dependency ordering |
| Circular dependency detection | Implemented | Raises `CircularDependencyError` |
| Tenure rules (7) | Implemented | total_years, current employer/role, longest tenure, career progression, gaps, career stage |
| Experience rules (7) | Implemented | strongest, leadership, cloud, technology breadth, domain, senior responsibility, career highlights |
| Confidence scoring | Partial | All rules return `confidence=1.0` — no variable confidence |
| Evidence packaging | Implemented | `EvidencePackageAssembler` sections findings by type |
| Deterministic execution | Implemented | Same profile → same results always |
| `analyze()` convenience method | Implemented | New in PKR-006.5; accepts profile directly |
| Report serialization | Implemented | `ReasoningReport.to_dict()` and `to_json()` |

### Artifact Generation

| Capability | Status | Details |
|---|---|---|
| Markdown CV generation | Implemented | `MarkdownCVGenerator` — section-based CV |
| DOCX CV generation | Implemented | `DocxCVGenerator` — delegates to Markdown, converts to DOCX |
| Markdown cover letter (generic) | Implemented | `MarkdownCoverLetterGenerator` — artifact-only output |
| Markdown cover letter (JD-aware) | Implemented | Same generator; set `job_description` on `ExportContract` for deterministic requirement matching and evidence reordering |
| Reasoning-aware generation | Implemented | `ReasoningFindings` on `ExportContract` consumed by CV + cover letter generators |
| Export contract building | Implemented | `ExportContractBuilder` resolves artifact, contexts, sources |
| Evidence selection | Implemented | `EvidenceSelector` filters sources by target context |
| Generator registry | Implemented | `GeneratorRegistry` with `default_generator_registry()` |

### Acquisition (Knowledge Ingestion)

| Capability | Status | Details |
|---|---|---|
| DOCX document reading | Implemented | `DocumentReader` — paragraphs + tables |
| Text normalization | Implemented | `TextExtractor` — whitespace/structure cleanup |
| LLM-based extraction | Implemented | `OpenAILLMExtractor` — OpenAI GPT-4o (requires API key) |
| Profile building | Implemented | `CanonicalProfileBuilder` with deduplication and normalization |
| YAML persistence | Implemented | `YamlWriter` — writes to `profiles/staging/` |
| Builder registry | Implemented | `BuilderRegistry` with entity-type-specific builders |

### CV Optimization

| Capability | Status | Details |
|---|---|---|
| Profile-CV comparison | Implemented | `CVOptimizer` finds elements not in CV |
| Relevance scoring | Implemented | Weighted by job description, target context, evidence strength |
| DOCX rendering | Implemented | `CVDocumentRenderer` applies recommendations to DOCX |
| Recommendation generation | Implemented | ADD/UPDATE/MOVE/REMOVE operations |

### REST API

| Capability | Status | Details |
|---|---|---|
| Health check | Implemented | `GET /health` |
| Schema listing | Implemented | `GET /schemas`, `GET /schemas/{entity}` |
| Entity validation | Implemented | `POST /validate/{entity}` |
| Entity CRUD | Implemented | Full CRUD on `/entities/{entity}[/{id}]` |
| Artifact generation | Implemented | `POST /generate/artifact`, `POST /generate/markdown-cv` |
| CV optimization | Implemented | `POST /optimize-cv` |
| Error handling | Implemented | Custom handlers for validation, business, and HTTP errors |

### CLI

| Capability | Status | Details |
|---|---|---|
| Schema inspection | Implemented | `schemas`, `schemas-info` commands |
| Validation | Implemented | `validate`, `doctor` commands |
| Entity management | Implemented | `create`, `show`, `list`, `search` commands |
| Artifact generation | Implemented | `generate-markdown-cv`, `generate-artifact` commands |
| CV optimization | Implemented | `optimize-cv` command |
| Profile acquisition | Implemented | `acquire-profile` command |

### Frontend

| Capability | Status | Details |
|---|---|---|
| SPA deployment artifact | Implemented | Built `index.html`, JS, CSS in `frontend/dist/` |
| Frontend source | Implemented | `frontend/src/` with TypeScript/React source, `frontend/package.json`, Vite config, Tailwind CSS, and type definitions |

### Testing

| Capability | Status | Details |
|---|---|---|
| Total tests | 555 | 21 files across all modules |
| Reasoning rules | 228 tests (41%) | Largest test area |
| Profile & knowledge | 94 tests (17%) | |
| Acquisition | 34 tests (6%) | |
| Core library | 15 tests (3%) | |
| API & CLI | 65 tests (12%) | 21 CLI + 44 REST API (fastapi) |
| Export & generators | 30 tests (5%) | |
| Test framework | pytest | `TestClient` for API, `CliRunner` for CLI |
| Integration tests | Partial | End-to-end acquisition (2 tests), pipeline integration |
| Mock usage | Minimal | `MockLLMExtractor` used in 2 acquisition integration tests to provide deterministic fake data; all other tests run against real filesystem and schemas |

## Capability Summary

| Domain | Implementation Status | Test Coverage |
|---|---|---|
| Schema Foundation | Complete | Core library tests |
| Profile Management | Complete | Core library tests |
| Knowledge Graph | Complete | 44 tests |
| Reasoning (Tenure) | Complete | 77 tests |
| Reasoning (Experience) | Complete | 86 tests |
| Reasoning (Engine) | Complete | 65 tests |
| Markdown CV Generation | Complete | 3 tests |
| DOCX CV Generation | Complete | 3 tests |
| Cover Letter Generation | Complete | 12 tests |
| Evidence Selection | Complete | 5 tests |
| Export Contract | Complete | 6 tests |
| CV Optimization | Complete | (part of pipeline tests) |
| DOCX CV Rendering | Complete | (part of pipeline tests) |
| Acquisition Pipeline | Complete | 2 integration tests |
| LLM Extraction | Complete | 20 tests |
| REST API | Complete | 11 tests |
| CLI | Complete | 10 tests |
| Frontend | Artifact only | No tests |
| PDF Generation | Not implemented | — |
| LLM Artifact Generation | Planned | — |
| Human Review Workflow | Placeholder | — |
| Job Search Management | Schema only | — |
