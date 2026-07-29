# 07 — Technical Debt

This document identifies **architectural debt only**. Style issues, small code smells, or localized refactoring opportunities are excluded.

---

## 1. Missing Abstraction: No Interface for KnowledgeGraph

**Severity**: Medium

**Evidence**: `ReasoningEngine.analyze()` at `careeros/reasoning/engine.py:29` imports the concrete `KnowledgeGraphBuilder` class:

```python
from careeros.knowledge import KnowledgeGraph, KnowledgeGraphBuilder
```

The `RuleContext` at `careeros/reasoning/models.py:32` also depends on the concrete `KnowledgeGraph`:

```python
@dataclass(frozen=True)
class RuleContext:
    graph: KnowledgeGraph
```

There is no abstract graph protocol or interface that the reasoning layer could depend on instead of the concrete implementation. This couples the reasoning engine to the knowledge graph's concrete type, making it impossible to substitute alternative graph implementations (e.g., an RDF-backed graph, a remote graph service, or a mock for testing).

**Impact**: The reasoning layer cannot be extracted as an independent package without also pulling in the knowledge module.

---

## 2. Duplicated Responsibility: ExportContract vs. Acquisition PersonData Models

**Severity**: Medium

**Evidence**: The acquisition package defines its own data classes in `careeros/acquisition/person_data.py`:

- `PersonData`, `ExperienceData`, `SkillData`, `EducationData`

The core library defines separate models in `careeros/export_contract.py`:

- `ExportSource`, `ExportContract`

And `careeros/models.py`:

- `EntityRecord`, `ValidationResult`

And reasoning has its own model layer in `careeros/reasoning/models.py`:

- `ReasoningResult`, `Evidence`, `EvidenceSet`, `RuleContext`, `AnalysisModel`, `EvidencePackage`, `ReasoningReport`

**Problem**: Person data flows from acquisition → profile builder → validator → export contract builder → generators. Each stage re-packages the data into its own structures. There is no single shared domain model that flows through the entire pipeline. This creates:

- Conversion overhead between representations
- Risk of field mismatch between layers
- Difficulty tracing data provenance

---

## 3. Tight Coupling: Generators Depend on MarkdownCVGenerator Internals

**Severity**: Low

**Evidence**: `careeros/generators/docx_cv.py` instantiates `MarkdownCVGenerator` and calls its `generate()` method, then parses the generated Markdown. `careeros/generators/markdown_cover_letter.py` imports `MarkdownCVGenerator` to reuse its `_person_name()` and `_education_label()` private helpers:

```python
from .markdown_cv import MarkdownCVGenerator
```

**Impact**: Changes to `MarkdownCVGenerator`'s Markdown output format or private helper methods will silently break dependent generators. The shared rendering logic (person names, date formatting, education labels) should live in a shared utility module rather than being private to one generator.

---

## 4. Missing Abstraction: No Formal Pipeline Contract Between Stages

**Severity**: Medium

**Evidence**: The acquisition pipeline in `careeros/acquisition/pipeline.py` hard-codes each step:

```python
class AcquisitionPipeline:
    def run(self, source: Path) -> Path:
        raw_text = DocumentReader().read(source)
        cleaned_text = TextExtractor().extract(raw_text)
        result = self.extractor.extract(cleaned_text)
        normalized = CanonicalProfileBuilder.normalize(result)
        profile = CanonicalProfileBuilder.build(...)
        ...
```

Similarly, `careeros/pipelines.py` hard-codes the generation pipeline:

```python
def generate_artifact(profile_file, artifact_id, output_format, ...):
    profile = ProfileLoader(schema_loader).load(profile_file)
    contract = ExportContractBuilder(schema_loader).build(profile, artifact_id)
    contract = EvidenceSelector().select(contract)
    generator = registry.resolve(artifact_type, output_format)
    return generator.generate(contract)
```

Pipeline steps are not composable — there is no `Pipeline` or `Stage` abstraction. Adding a step (e.g., logging, caching, transformation) requires modifying existing functions.

---

## 5. Extension Limitation: GeneratorRegistry Has No Plugin Discovery

**Severity**: Low

**Evidence**: `careeros/generators/registry.py` stores generators in a hard-coded dict:

```python
class GeneratorRegistry:
    def __init__(self):
        self._generators: dict[tuple[str, str], ArtifactGenerator] = {}
    def register(self, artifact_type, output_format, generator):
        ...
```

And `default_generator_registry()` manually instantiates all three generators. There is no auto-discovery mechanism (e.g., entry points, scanning, or a plugin system). Adding a new generator requires modifying application code.

---

## 6. Scalability Limitation: In-Process Synchronous Architecture

**Severity**: Low (for current scale)

**Evidence**: All operations in CareerOS are synchronous and in-process:

- `ReasoningEngine.run()` executes rules sequentially in a single thread
- `AcquisitionPipeline.run()` processes one document at a time
- `FileSystemRepository` stores entities as individual JSON files with no indexing

There is no caching layer, no async processing, no background task queue, and no database. The filesystem-backed repository will become a bottleneck beyond a few hundred entities.

---

## 7. Missing Dependency Declaration

**Severity**: Medium

**Evidence**: `careeros/acquisition/llm_extractor.py` imports and uses `httpx` for HTTP calls to OpenAI:

```python
import httpx
```

But `pyproject.toml` does not list `httpx` as a dependency. The `httpx` package must be installed independently for the acquisition pipeline to function.

---

## 8. Inconsistent Profile ID Resolution

**Severity**: Low

**Evidence**: Profile ID is resolved in multiple places with different fallback logic:

- `ReasoningEngine._resolve_profile_id()` at `careeros/reasoning/engine.py:100`: `person.get("id", "unknown")`
- `export_contract.py` may resolve entity IDs differently
- Acquisition generates IDs independently via `PersonData.id`

**Impact**: No single authority for profile identity. The same profile might be known by different IDs depending on the pipeline stage.

---

## 9. Overlapping API Endpoints

**Severity**: Low

**Evidence**: `api/main.py` defines two paths for entity creation:

- `POST /create/{entity}` (returns 200)
- `POST /entities/{entity}` (returns 201)

Both perform the same operation but differ in response status code and follow different URL conventions (legacy `/create/` vs. resource-oriented `/entities/`). This creates API surface confusion.

---

## Summary of Debt by Priority

| Priority | Issue | Impact |
|---|---|---|
| Medium | No KnowledgeGraph interface | Prevents reasoning from being independently packaged |
| Medium | Duplicated domain models across layers | Conversion overhead, field mismatch risk |
| Medium | No formal pipeline abstraction | Cannot compose or extend pipelines |
| Medium | Missing `httpx` dependency declaration | Runtime failure on acquisition |
| Low | Generators coupled to MarkdownCVGenerator internals | Brittle cross-generator dependencies |
| Low | No generator auto-discovery | Adding generators requires code changes |
| Low | Synchronous in-process architecture | Limited scalability |
| Low | Inconsistent profile ID resolution | No single identity authority |
| Low | Overlapping API endpoints | API surface confusion |
