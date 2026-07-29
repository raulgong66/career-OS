# Profile Builder Agent

## Overview

The Profile Builder Agent is the first implementation of the Professional Knowledge Acquisition Framework. It handles acquisition from local document sources (DOC, DOCX, PDF, Markdown) and produces canonical profile YAML files.

As the initial agent, it establishes the pattern for all future acquisition agents: parse, extract, normalize, validate, present for human review, and generate the canonical profile.

## Scope

The Profile Builder Agent is responsible for:

- Ingesting CV/resume documents in DOC, DOCX, PDF, and Markdown formats
- Extracting professional knowledge entities (person, experiences, education, certifications, skills, achievements, projects, organizations)
- Assembling a complete canonical profile YAML file
- Presenting the extracted profile for human review and correction
- Writing the approved profile to `profiles/staging/` (with later promotion to `profiles/` upon review)

It is explicitly **not** responsible for:

- Artifact generation (CV, cover letter, LinkedIn profile generation — handled by the delivery pipeline)
- Profile optimization or tailoring
- Cross-profile comparison or analytics
- Connecting to external APIs (LinkedIn, Credly, GitHub — future agents)

## Source Handling

### DOC / DOCX

- **Parsing.** Binary conversion to extract text content while preserving section structure, formatting hints, and embedded metadata.
- **Extraction focus.** Chronological experience sections, education tables, certification lists, skill inventories, contact information blocks.
- **Heuristics.** Exploit document structure (headings, bullet lists, tables) to identify entity boundaries.

### PDF

- **Parsing.** Text extraction with layout analysis to reconstruct reading order and section hierarchy.
- **Extraction focus.** Same as DOC/DOCX, but with additional attention to multi-column layouts and text that spans pages.
- **Limitations.** PDF extraction may lose some formatting context; the agent should flag low-confidence extractions.

### Markdown

- **Parsing.** AST-based parsing to produce a structured, section-aware document tree.
- **Extraction focus.** Leverages explicit section headings, bullet lists, code blocks (for projects), and link references.
- **Advantage.** Markdown's explicit structure typically yields the highest extraction confidence.

## Agent Workflow

The Profile Builder Agent implements the eight-stage acquisition pipeline:

```
Source Document(s) → Parse → Extract → Normalize → Review Hook → Validate → Write → Move on Approval
```

- **Parse → Extract → Normalize** — document text is parsed, cleaned, and passed through an LLM for structured entity extraction, then normalized (dedup, sort, date/company cleaning).
- **Review Hook** — a pass-through callback that will be replaced by the Human Review interface. It receives the normalized `ExtractionResult` and can modify entities before profile assembly.
- **Validate → Write** — the assembled profile is validated against `schemas/profile.schema.json` and written to the staging directory.
- **Move on Approval** — reviewed and approved profiles are moved from staging to the canonical `profiles/` directory (future milestone).

### Input

The agent accepts:

- One or more file paths (source documents)
- An optional person identifier (if the profile already exists, the agent reconciles rather than replaces)
- An optional target profile file path (defaults to `profiles/staging/{person-id}-profile.yaml`)

### Processing

1. **Parse.** Each source document is parsed into a `ParsedDocument` with section hierarchy and metadata.
2. **Extract.** An LLM-based extraction step identifies professional entities from the parsed document. The extraction prompt is schema-aware, producing output that maps directly to canonical profile entity types.
3. **Normalize.** Extracted entities are normalized: dates are standardized, organizations are resolved, skills are deduplicated, relationships are inferred. Source document name and extraction timestamp are recorded for traceability.
4. **Validate.** The assembled profile is validated against the canonical profile schema and business rules.
5. **Review Hook.** A pass-through callback (currently a no-op) that future Human Review will replace with an interactive review step.
6. **Generate.** The canonical profile YAML is written to `profiles/staging/`. Every profile includes source traceability metadata (`extensions._acquisition`). Source documents are tracked as evidence (future milestone).

### Output

- A validated canonical profile YAML file in `profiles/staging/` (awaiting human review before promotion to `profiles/`)
- Source traceability metadata (`extensions._acquisition.sourceDocument`, `extensions._acquisition.extractionTimestamp`) embedded in every generated profile
- Source documents preserved in an evidence directory with references embedded in the profile (future milestone)
- An acquisition record documenting the pipeline execution

## Interaction with Existing Architecture

The Profile Builder Agent produces profiles that are consumed by the existing delivery pipeline:

```
                   Profile Builder Agent
                           │
                           ▼
           Staging Profile (profiles/staging/*.yaml)
                           │
                     Human Review
                           │
                      (promoted)
                           │
                           ▼
              Canonical Profile (profiles/*.yaml)
                           │
                           ▼
     ┌─────────────────────────────────────┐
     │  Existing Delivery Pipeline         │
     │  ProfileLoader → ExportContract →   │
     │  EvidenceSelector → Generators      │
     └─────────────────────────────────────┘
```

This means:

- **No changes to the delivery pipeline.** The agent produces standard canonical profile YAML that ProfileLoader can read.
- **Validation reuse.** The agent uses the same schema (`schemas/profile.schema.json`) and validator that the delivery pipeline uses.
- **Profile backwards compatibility.** Profiles created by the agent are indistinguishable from manually authored profiles.

## Human Review Interface

The review step requires an interactive interface (CLI-based or simple web UI) that presents:

1. **Extracted entities grouped by type** (person, experiences, organizations, etc.)
2. **Source attribution** for each field — the original text is shown alongside the extracted value
3. **Confidence indicators** — low-confidence extractions are visually flagged
4. **Diff view** when updating an existing profile
5. **Inline editing** — the reviewer can correct any field
6. **Approve / Reject / Edit-and-Approve actions**

For the Beta milestone, a CLI-based review workflow is sufficient. A web-based review UI can follow in a later iteration.

## Acceptance Criteria

The Profile Builder Agent is complete when:

1. A DOC source document can be parsed, extracted, and converted into a validated canonical profile YAML.
2. A DOCX source document can be processed identically.
3. A PDF source document can be processed with confidence indicators for each extracted field.
4. A Markdown source document can be processed with high extraction confidence.
5. The extracted profile validates against `schemas/profile.schema.json`.
6. The human reviewer can inspect, correct, and approve or reject the extracted profile.
7. On approval, the profile is written to `profiles/staging/` with source traceability metadata, and can be promoted to `profiles/` after review.
8. The resulting profile can be loaded by the existing `ProfileLoader` and used in the delivery pipeline without modification.

## Future Considerations

- **Batch processing.** Support ingesting multiple source documents in a single run, with cross-source reconciliation.
- **Incremental updates.** Re-run acquisition on a single new source document and merge into an existing profile without re-processing all sources.
- **Review history.** Maintain a decision log of human review actions for auditability.
- **Confidence thresholds.** Configurable thresholds below which extraction is automatically flagged for human review.
