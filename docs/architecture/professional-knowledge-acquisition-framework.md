# Professional Knowledge Acquisition Framework

## Overview

The Professional Knowledge Acquisition Framework is the architectural capability responsible for ingesting professional knowledge from external sources and producing validated canonical profile data. It sits opposite the existing artifact generation pipeline: acquisition brings knowledge *in*, delivery pushes knowledge *out*.

```
External Sources → [Acquisition Framework] → Canonical Profile → [Delivery Pipeline] → Artifacts
```

The framework is designed for extensibility by source type, with a common pipeline shared across all sources.

## Design Principles

1. **Source traceability.** Every fact in the canonical profile must be attributable to a source location, with the source preserved as evidence.
2. **Human verification.** Automated extraction is fallible. All acquired data passes through a human review gate before entering the canonical repository.
3. **Idempotent re-acquisition.** Running acquisition on the same source twice should produce the same profile data, modulo corrections made during review.
4. **Progressive enrichment.** Acquisition from multiple sources should merge and reconcile data, not overwrite. A LinkedIn import should fill gaps left by a DOC import, not replace it.
5. **Schema alignment.** The framework produces data conforming to the canonical profile schema defined in `schemas/profile.schema.json`. It does not define its own data model.

## Supported Acquisition Sources

### Current (CareerOS Beta)

| Source | Format | Handler | Status |
|---|---|---|---|
| CV document | DOC | Profile Builder Agent | Planned |
| CV document | DOCX | Profile Builder Agent | Planned |
| CV document | PDF | Profile Builder Agent | Planned |
| Professional summary | Markdown | Profile Builder Agent | Planned |

### Future

| Source | Format | Handler | Notes |
|---|---|---|---|
| LinkedIn | API / export | LinkedIn connector | Profile data, recommendations, skills |
| GitHub | API | GitHub connector | Projects, languages, contributions |
| Credly | API | Credly connector | Verified certifications with badges |
| Microsoft Learn | API / transcript | Microsoft Learn connector | Training paths, assessments, certifications |
| LinkedIn API | API | LinkedIn connector | Automated profile sync |
| Other connectors | TBD | TBD | Extensible via handler interface |

## Common Acquisition Pipeline

Every acquisition source follows the same six-stage pipeline:

```
Source Document → [1. Parsing] → [2. Extraction] → [3. Normalization] → [4. Validation] → [5. Human Review] → [6. Canonical Profile Generation]
```

### Stage 1: Parsing

Convert the source document into a machine-readable intermediate representation.

| Source | Parsing Strategy |
|---|---|
| DOC | Binary format conversion → text extraction |
| DOCX | XML parsing → structured content tree |
| PDF | Text extraction with layout analysis |
| Markdown | AST parsing → section-aware document tree |
| API sources | JSON response → typed record set |

**Output:** A `ParsedDocument` containing raw text, section hierarchy, metadata (author, date, format), and any detected structure (tables, lists, headings).

**Traceability:** Each extracted text span is tagged with its source location (page, paragraph, line, section path).

### Stage 2: Extraction

Identify and extract professional knowledge entities from the parsed document.

The extraction stage uses LLM-based inference for unstructured content, combined with structural heuristics where the document format provides explicit structure (e.g., tables in DOCX, section headings in Markdown).

**Extracted entity types** correspond to canonical profile entities:

- Person identity and contact information
- Professional summaries and positioning statements
- Experiences with organizations, roles, dates, and responsibilities
- Education records with institutions, degrees, and dates
- Certifications with issuing bodies and credential identifiers
- Skills with proficiency indicators
- Achievements with measurable outcomes
- Projects with descriptions and technologies
- Evidence references (links, document citations)

**Output:** An `ExtractionResult` containing extracted entities, each annotated with:
- Source location references
- Confidence score (high / medium / low)
- Any alternative interpretations or ambiguities detected

### Stage 3: Normalization

Transform extracted data into a consistent, schema-compatible representation.

Normalization handles:

- **Date normalization.** Converting relative dates ("present", "current") to explicit boundaries, normalizing date formats.
- **Organization name resolution.** Detecting variant names for the same organization (e.g., "IBM", "International Business Machines").
- **Location normalization.** Converting location strings to structured location objects.
- **Language normalization.** Mapping language names to standard codes.
- **Skill deduplication.** Merging equivalent skill expressions ("Kubernetes", "K8s", "k8s administration").
- **Relationship inference.** Connecting experiences to organizations, skills to experiences, achievements to their context.

**Output:** A `NormalizedProfile` with all entities in canonical schema format, ready for validation.

### Stage 4: Validation

Validate the normalized profile against the canonical profile schema and business rules.

Validation has two layers:

1. **Structural validation.** Ensures the normalized data conforms to `schemas/profile.schema.json` — required fields, correct types, valid references.
2. **Business rule validation.** Checks rules beyond the schema:
   - Date ranges are chronologically valid
   - Required relationships exist (experiences reference known organizations)
   - No conflicting data across sources (same experience with different dates)
   - No placeholder values remain (`<REQUIRED>`, `<TBD>`)

**Output:** A `ValidationReport` listing passed checks, warnings, and errors. Failed validation halts the pipeline before human review.

### Stage 5: Human Review

A mandatory review gate where a human inspects the extracted and validated profile data before it enters the canonical repository.

The review interface presents:

- **Diff view.** Proposed changes compared to any existing profile data (green = new, yellow = changed, red = removed).
- **Source context.** For each extracted fact, the original source text is shown alongside the extracted value.
- **Confidence indicators.** Low-confidence extractions are highlighted for special attention.
- **Conflict resolution.** When multiple sources disagree, the reviewer chooses which value to accept.
- **Editorial corrections.** The reviewer may add, remove, or modify any field before approval.

**Outcomes:**
- **Approved.** The profile data passes to the generation stage.
- **Approved with edits.** The reviewer makes corrections, then approves.
- **Rejected.** The pipeline halts; the source document may need to be updated and re-submitted.
- **Flagged for re-extraction.** Extraction quality was insufficient; the source handler is refined.

### Stage 6: Canonical Profile Generation

Write the approved profile data to the canonical profile repository (`profiles/`).

This stage produces one or more files:

- **Profile YAML.** The canonical profile file (e.g., `profiles/raul-gongora-profile.yaml`).
- **Source references.** Source documents are copied to a tracked evidence location with their references embedded in the profile.
- **Acquisition record.** A metadata record documenting which sources were used, when acquisition ran, and what human review decisions were made.

## Cross-Source Reconciliation

When acquisition runs against a source for a person who already has canonical profile data, the framework performs reconciliation:

1. **Match existing entities** by stable IDs (organization IDs, certification IDs, experience date ranges).
2. **Detect conflicts.** Same entity with different attribute values is flagged for human review.
3. **Detect additions.** New entities not present in the canonical profile are proposed as additions.
4. **Detect removals.** Entities in the canonical profile but absent from all active sources are flagged as potentially stale.

Reconciliation is advisory. The human reviewer makes the final decision on all merges, conflicts, and removals.

## Extensibility Model

New source types are added by implementing a **source handler** that conforms to the common pipeline interface:

```
SourceHandler
├── can_handle(source) → bool
├── parse(source) → ParsedDocument
├── extract(parsed) → ExtractionResult
└── source_metadata → { name, version, format }
```

The normalization, validation, human review, and profile generation stages are shared across all handlers. Only parsing and extraction are source-specific.

This means adding a new connector (e.g., Credly) requires implementing two functions — `parse` and `extract` — while inheriting the full pipeline.

## Builder Architecture

Entity builders convert normalized data objects into canonical profile dicts. The `CanonicalProfileBuilder` orchestrates them via the `BuilderRegistry`.

### Lifecycle

Each builder exposes three phases:

```
normalize(items) → prepare(items, all_data) → build_many(items, context) → dicts
```

1. **`normalize(items)`** — clean, deduplicate, sort individual entities.
2. **`prepare(items, all_data)`** — cross-entity enrichment (e.g., skill evidence from experiences). Default is a no-op.
3. **`build_many(items, context)`** — convert normalized entities to profile dicts, populating `BuilderContext` as needed.

### How to add a new entity builder

**1. Create the builder class** in `careeros/acquisition/builders/`:

```python
from typing import Any, ClassVar
from ..person_data import EducationData  # or whatever entity
from .base import BaseBuilder, BuilderContext

class EducationBuilder(BaseBuilder):
    entity_type: ClassVar[type] = EducationData
    profile_key: ClassVar[str] = "education"
    extraction_field: ClassVar[str] = "education"
    # set singular=True if this maps to a single dict (like person)

    def normalize(self, items: list) -> list:
        # clean, dedup, sort
        ...

    def build_many(self, items: list, context: BuilderContext) -> list[dict[str, Any]]:
        # convert to profile-compatible dicts
        ...
```

Fields each builder must declare:

| ClassVar | Purpose | Example |
|---|---|---|
| `entity_type` | The dataclass type this builder handles | `EducationData` |
| `profile_key` | Key in the profile dict | `"education"` |
| `extraction_field` | Attribute name on `ExtractionResult` | `"education"` |
| `singular` | `True` if output is a single dict (person), `False` for lists | `False` |

**2. Register in** `CanonicalProfileBuilder.__init__`:

```python
self.registry.register(EducationData, EducationBuilder())
```

That is the only change required. The `normalize()` and `build()` methods on `CanonicalProfileBuilder` iterate the registry generically and require no modifications.

### Builder Registry

- Registration is ordered and deterministic (insertion order).
- Duplicate registration raises `ValueError`.
- Non-builder objects raise `TypeError`.
- `get(entity_type)` returns `None` for unregistered types.

### Builder Independence

- Builders never invoke other builders.
- Cross-entity data flows through `BuilderContext` (mutable context passed to `build_many`) or `all_data` (read-only dict of all entity lists passed to `prepare`).
- The orchestrator (`CanonicalProfileBuilder`) is the only component that coordinates multiple builders.

### Shared Utilities

Shared helpers in `careeros/acquisition/utils.py`:

| Function | Purpose |
|---|---|
| `normalize_date(str) → str` | Standardize date strings, replace "present"/"now" with "" |
| `extract_year(str) → int\|None` | Extract 4-digit year from a date string |
| `extract_month(str) → int\|None` | Extract month number from abbreviated month name |
| `normalize_company(str) → str` | Normalize company names (lowercase, strip special chars, known abbreviations) |
