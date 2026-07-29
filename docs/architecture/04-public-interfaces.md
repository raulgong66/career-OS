# 04 — Public Interfaces

## Python Public API (`careeros` package)

The `careeros/__init__.py` re-exports symbols from all submodules, forming the public surface of the core library.

### Stable Interfaces

| Symbol | Kind | Stable Since |
|---|---|---|
| `CareerOSException` | Exception base class | 0.1.0 |
| `ValidationResult` | Data class with `to_dict()` | 0.1.0 |
| `EntityRecord` | Data class with `to_dict()` | 0.1.0 |
| `ExportContract` | Data class | 0.1.0 |
| `ExportSource` | Data class | 0.1.0 |
| `ProfileLoader` | Class | 0.1.0 |
| `SchemaLoader` | Class | 0.1.0 |
| `EntityValidator` | Class | 0.1.0 |
| `FileSystemRepository` | Class | 0.1.0 |
| `EvidenceSelector` | Class | 0.1.0 |
| `GeneratorRegistry` | Class | 0.1.0 |
| `MarkdownCVGenerator` | Class | 0.1.0 |
| `MarkdownCoverLetterGenerator` | Class | 0.1.0 |
| `DocxCVGenerator` | Class | 0.1.0 |
| `CVOptimizer` | Class | 0.1.0 |
| `Recommendation` | Data class | 0.1.0 |
| `CVDocumentRenderer` | Class | 0.1.0 |
| `ExportContractBuilder` | Class | 0.1.0 |
| `default_generator_registry` | Function | 0.1.0 |
| `generate_artifact` | Function | 0.1.0 |
| `generate_markdown_cv` | Function | 0.1.0 |

### Reasoning Interfaces

| Symbol | Kind | Stable Since | Notes |
|---|---|---|---|
| `ReasoningResult` | Frozen dataclass | 0.1.0 | Atomic output of a rule |
| `RuleContext` | Frozen dataclass | 0.1.0 | Input context for rules |
| `AnalysisModel` | Frozen dataclass | 0.1.0 | Output of `engine.run()` |
| `ReasoningReport` | Frozen dataclass | 0.1.0 | Output of `engine.analyze()`; new |
| `EvidencePackage` | Frozen dataclass | 0.1.0 | Output of assembler |
| `Rule` | Abstract base class | 0.1.0 | Extend to create rules |
| `RuleRegistry` | Class | 0.1.0 | Register/lookup rules |
| `ReasoningEngine` | Class | 0.1.0 | `run()` and `analyze()` methods |
| `EvidencePackageAssembler` | Class | 0.1.0 | Transforms analysis to package |
| `RegistryError` | Exception | 0.1.0 | Base for registry errors |
| `DuplicateRuleError` | Exception | 0.1.0 | Duplicate rule registration |
| `MissingDependencyError` | Exception | 0.1.0 | Missing rule dependency |
| `CircularDependencyError` | Exception | 0.1.0 | Cycle in dependency graph |

### Acquisition Interfaces

| Symbol | Kind | Stable Since | Notes |
|---|---|---|---|
| `AcquisitionPipeline` | Class | 0.1.0 | Orchestrates ingestion |
| `DocumentReader` | Class | 0.1.0 | DOCX → text |
| `TextExtractor` | Class | 0.1.0 | Text normalization |
| `LLMExtractor` | Abstract class | 0.1.0 | Extend to implement LLM extraction |
| `OpenAILLMExtractor` | Class | 0.1.0 | Concrete OpenAI implementation |
| `PersonData` | Dataclass | 0.1.0 | Extracted person data |
| `YamlWriter` | Class | 0.1.0 | Profile YAML persistence |
| `CanonicalProfileBuilder` | Class | 0.1.0 | Profile assembly from extracted data |

### Knowledge Graph Interfaces

| Symbol | Kind | Stable Since | Notes |
|---|---|---|---|
| `GraphNode` | Frozen dataclass | 0.1.0 | Graph node |
| `GraphEdge` | Frozen dataclass | 0.1.0 | Graph edge |
| `KnowledgeGraph` | Immutable class | 0.1.0 | Graph with query methods |
| `KnowledgeGraphBuilder` | Class | 0.1.0 | Builds graph from profile dict |

## REST API Endpoints

**Framework**: FastAPI 1.0.0, served via `uvicorn api.main:app`

| Method | Path | Purpose | Request | Response |
|---|---|---|---|---|
| GET | `/health` | Health check | — | `{"status": "ok"}` |
| GET | `/version` | API version | — | `{"version": "1.0.0"}` |
| GET | `/schemas` | List schema entities | — | `["profile", "skill", ...]` |
| GET | `/schemas/{entity}` | Schema metadata | — | `{title, description, version}` |
| POST | `/validate/{entity}` | Validate payload | JSON body | `{valid: bool, errors: [...]}` |
| POST | `/create/{entity}` | Create entity (legacy) | JSON body | `EntityRecord` |
| POST | `/search/{entity}` | Search entities | `{field, value}` | `[EntityRecord]` |
| POST | `/generate/markdown-cv` | Generate Markdown CV | `{profile_file, artifact_id}` | Markdown text |
| POST | `/generate/artifact` | Generate any artifact | `{profile_file, artifact_id, output_format}` | Generated content |
| POST | `/optimize-cv` | CV optimization | `{profile_file, artifact_id, job_description?}` | `[Recommendation]` |
| GET | `/entities/{entity}` | List entities | — | `[EntityRecord]` |
| GET | `/entities/{entity}/{id}` | Get entity | — | `EntityRecord` |
| POST | `/entities/{entity}` | Create entity (201) | JSON body | `EntityRecord` |
| PUT | `/entities/{entity}/{id}` | Update entity | JSON body | `EntityRecord` |
| DELETE | `/entities/{entity}/{id}` | Delete entity | — | 204 No Content |

**Note**: Both `POST /create/{entity}` (legacy) and `POST /entities/{entity}` create entities, with the latter returning HTTP 201.

## CLI Commands

**Framework**: Typer 0.12+, with Rich console output.

Entry point: `careeros` (defined in `pyproject.toml` as `careeros = "careeros_cli.main:app"`)

| Command | Arguments | Options | Purpose |
|---|---|---|---|
| `version` | — | — | Print version |
| `doctor` | — | — | Validate installation |
| `schemas` | — | — | List schemas |
| `schemas-info` | `entity` | — | Schema metadata |
| `validate` | `entity`, `file_path` | — | Validate file |
| `create` | `entity`, `output_file` | — | Generate starter entity |
| `show` | `entity`, `file_path` | — | Pretty-print entity |
| `list` | `entity`, `directory` | — | List entity files |
| `search` | `entity`, `field`, `value` | `--directory` | Search profiles |
| `generate-markdown-cv` | `profile_file`, `artifact_id`, `output_file` | — | Generate Markdown CV |
| `generate-artifact` | `profile_file`, `artifact_id`, `output_format`, `output_file` | — | Generate any artifact |
| `optimize-cv` | `profile_file`, `artifact_id` | `--job-desc`, `--docx`, `--output` | Optimization |
| `acquire-profile` | `source` | `--output` | Acquire from DOCX |

## Extension Points

### Rule Registry (Stable)

The `Rule` abstract base class and `RuleRegistry` form the primary extension mechanism. New rules are created by subclassing `Rule` and registering with the registry:

```python
class MyRule(Rule):
    id = "my_rule"
    name = "My Rule"
    description = "..."
    def execute(self, context: RuleContext) -> list[ReasoningResult]: ...

registry.register(MyRule())
```

### Generator Registry (Stable)

The `ArtifactGenerator` protocol and `GeneratorRegistry` allow adding new output formats:

```python
class MyGenerator:
    supported_artifact_types = {"CV"}
    def generate(self, contract: ExportContract) -> str: ...

registry.register("CV", "html", MyGenerator())
```

### Builder Registry (Internal)

The `BuilderRegistry` in `acquisition/builders/base.py` maps entity types to builders. Currently used within acquisition only — not exported as a public extension point.

### LLMExtractor (Internal)

The `LLMExtractor` abstract class allows alternative LLM providers. Only `OpenAILLMExtractor` exists currently.

## Interface Stability Summary

| Interface | Stability | Notes |
|---|---|---|
| Python core library exports | Stable | Backward-compatible since 0.1.0 |
| CLI commands | Stable | All commands functional |
| REST API endpoints | Stable | 14 endpoints, overlapping legacy paths |
| Rule API (`Rule` base class) | Stable | 14 concrete implementations |
| Generator API (`ArtifactGenerator` protocol) | Stable | 3 concrete implementations |
| `ReasoningReport` | New (0.1.0) | Added in PKR-006.5 |
| Builder API (`BaseBuilder`) | Internal | Used only in acquisition |
| `LLMExtractor` API | Internal | Abstract but only one implementation |
| Frontend API | Unknown | No source code in repo |
