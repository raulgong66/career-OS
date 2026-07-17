# ADR 0003: Canonical Profile Schema

## Status

Accepted

## Context

CareerOS needs a machine-validatable structure for the canonical professional profile defined in `docs/data-model/Canonical-Profile-Model.md`. The schema must support generated artifacts such as CVs, resumes, LinkedIn profiles, portfolios, cover letters, and interview preparation without making any one output format the source of truth.

## Decision

CareerOS will use JSON Schema Draft 2020-12 for the canonical profile schema in `schemas/profile.schema.json`.

Referenceable entities require stable IDs so relationships between experiences, organizations, projects, skills, achievements, evidence, education, certifications, artifacts, and target contexts can be maintained without duplicating data.

Canonical objects are closed with `additionalProperties: false`, and each extensible entity provides an explicit `extensions` object. This keeps the core schema reviewable while preserving a controlled path for future additions.

The schema validates structure only. Business rules, such as whether a date range is chronologically valid or whether evidence sufficiently supports a claim, are intentionally left to later validation layers or review workflows.

## Consequences

The schema can catch malformed canonical profile structure early while remaining implementation-independent. Future schema changes that alter entity shape, reference behavior, or extension rules should be recorded in an ADR or other designated decision log.
