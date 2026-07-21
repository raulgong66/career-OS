# CareerOS Schemas

## Purpose

This directory contains the shared schema foundation for CareerOS. These files define reusable definitions and conventions that future entity schemas can reference.

## Schema Purpose

- common.schema.json: reusable structural definitions such as identifiers, dates, addresses, links, and references.
- metadata.schema.json: a reusable metadata object for entities that need lifecycle and ownership information.
- enums.schema.json: centralized shared enumerations for employment, status, visibility, file types, and other common values.

## Reuse Conventions

- Reuse existing definitions before introducing new ones.
- Keep schemas deterministic and modular.
- Prefer reusable $defs over duplicated structures.
- Reference shared schemas through stable absolute $id values.
- Keep descriptions explicit and production-ready.

## Versioning

All schemas use semantic versioning and should evolve conservatively.

## Validation

Schemas should be validated with a Draft 2020-12 compatible validator.
