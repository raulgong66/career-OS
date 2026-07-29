# 00 — Executive Summary

## What Is CareerOS Today?

CareerOS is a Python 3.11+ command-line toolkit and REST API for managing professional career data. It ingests source documents (DOCX), extracts structured profile data (optionally via LLM), validates against a JSON Schema-defined canonical profile, runs deterministic reasoning rules over the data, and generates career artifacts (CVs, cover letters) in Markdown and DOCX formats.

The system is implemented as a single Python package (`careeros/`) with two entry-point applications (`careeros-cli`, `careeros-api`), ~18 JSON Schema files, 14 reasoning rules, 3 artifact generators, and 422 tests.

## What Problem Does It Solve?

CareerOS addresses the fragmentation of professional data across multiple formats and platforms. It provides a single canonical profile schema as the source of truth, deterministic analysis of that data via reasoning rules, and portable artifact generation. The reasoning layer eliminates hallucination and non-determinism from AI-generated career documents by computing analytical facts before any LLM interaction.

## Architectural Style

CareerOS follows a layered architecture with domain-driven boundaries:

- **Canonical Schema** — JSON Schema (Draft 2020-12) defines all entities
- **Acquisition Layer** — ingest, extract, normalize, validate
- **Knowledge Layer** — in-memory property graph built from the canonical profile
- **Reasoning Layer** — deterministic rules consuming the graph, producing findings
- **Generation Layer** — registries of generators consuming export contracts
- **Delivery Layer** — CLI (Typer) and REST API (FastAPI) exposing the above

No external dependencies beyond stdlib `dataclasses` for domain models. All reasoning is synchronous, in-process, and deterministic.

## Major Building Blocks

| Block | Location | Responsibility |
|---|---|---|
| Schema Foundation | `schemas/*.schema.json` | Entity definitions, validation rules |
| Core Library | `careeros/` | Shared models, validation, repositories, pipelines |
| Knowledge Graph | `careeros/knowledge/` | In-memory graph representation of a profile |
| Reasoning Engine | `careeros/reasoning/` | Deterministic rule execution, evidence packages |
| Acquisition | `careeros/acquisition/` | Document ingestion and profile construction |
| Generators | `careeros/generators/` | Artifact generation (Markdown CV, DOCX CV, cover letter) |
| Optimization | `careeros/optimizer.py` | CV optimization recommendations |
| CLI | `careeros_cli/main.py` | Typer-based command-line interface |
| API | `api/main.py` | FastAPI-based REST interface |
| Frontend | `frontend/dist/` | Built React SPA (deployment artifact) |
| Tests | `tests/` | 422 tests across 19 files |
