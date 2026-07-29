# ADR 0004: Professional Knowledge Acquisition Framework

## Status

Accepted

## Context

CareerOS currently relies on manually authored canonical profile YAML files as the source of truth for all artifact generation. The existing architecture — from `ProfileLoader` through `ExportContractBuilder` and `EvidenceSelector` to `MarkdownCVGenerator` — assumes a complete, validated profile already exists in `profiles/`.

This creates a gap: there is no documented path for creating or updating profile data from external sources. Professional knowledge typically exists in diverse formats — CV documents (DOC, DOCX), LinkedIn profiles, certification badges, GitHub repositories, and learning transcripts — each with different structures and reliability characteristics.

CareerOS needs an architectural capability that:

- Ingests professional knowledge from external sources
- Transforms unstructured or semi-structured input into canonical profile data
- Preserves source traceability so every canonical fact can be attributed
- Supports human review before data enters the canonical repository
- Accommodates multiple source types without coupling the core system to any single format

## Decision

CareerOS will adopt a **Professional Knowledge Acquisition Framework** as a first-class architectural capability, separated from knowledge delivery.

### Separation of Acquisition from Delivery

The existing artifact generation pipeline (profile → CV, cover letter, etc.) is a **knowledge delivery** capability. It assumes canonical data already exists and transforms it into audience-specific views.

The acquisition framework is the **knowledge ingestion** capability. It produces canonical data from external sources.

These two capabilities are separated because:

1. **Different lifecycles.** Acquisition is an occasional, intentional act (a new role, a certification update). Delivery is a repetitive, per-opportunity act (generate a tailored CV for each job application).

2. **Different quality guarantees.** Acquisition requires human review before data enters the canonical repository. Delivery operates on already-validated data.

3. **Different failure modes.** Acquisition errors produce incorrect profile data, which cascades into every generated artifact. Delivery errors affect only a single output.

4. **Different evolution paths.** Acquisition must adapt to new source formats (Credly, LinkedIn export, GitHub API). Delivery must adapt to new output formats and tailoring strategies. Coupling them would slow both.

### Agent-Based Acquisition Model

The acquisition framework will use an **agent-based model** rather than format-specific importers. An acquisition agent:

- Encapsulates the full pipeline for a class of sources: parsing, extraction, normalization, validation, and canonical profile assembly
- Uses LLM-based extraction for unstructured sources where rule-based parsing is insufficient
- Maintains traceability from extracted facts back to source locations
- Integrates with a shared human review gate before persisting to the canonical repository

This model is preferred over format-specific importers (e.g., `doc-importer.py`, `linkedin-importer.py`) because:

1. **Format diversity.** A single agent can handle multiple related source types (DOC, DOCX, PDF as text) with shared extraction logic, while importers encourage duplication.

2. **Extraction quality.** Unstructured documents contain implicit relationships (e.g., which organization an experience belongs to) that are better resolved by an LLM with profile schema awareness than by regex or template matching.

3. **Cross-source reconciliation.** An agent can detect contradictions across sources (e.g., LinkedIn says "2020–2024" while the CV says "2020–2023") and flag them for human review. Format importers operate in isolation and cannot reconcile.

4. **Future-proofing.** New source types (Credly API, Microsoft Learn transcript, GitHub README) can be supported by extending the agent's source handlers without changing the pipeline architecture.

## Consequences

1. The existing delivery pipeline remains unchanged. Acquisition and delivery share the canonical profile schema but evolve independently.

2. Human review becomes an explicit architectural step. No data enters `profiles/` without review, even if extracted automatically.

3. Source documents used for acquisition become tracked evidence in the repository, linked to canonical profile data through source references.

4. Future source connectors (LinkedIn, Credly, GitHub, Microsoft Learn) will be implemented as handlers within the acquisition framework, not as standalone import scripts.

5. The first implementation of the framework will be the Profile Builder Agent, which handles DOC, DOCX, PDF, and Markdown source documents.
