# ADR 0006: Profile Acquisition and Import Lifecycle

## Status

Accepted

## Context

CareerOS imports professional CV documents through the Profile Acquisition pipeline (ADR 0004). The import lifecycle encompasses document upload, LLM-based extraction, deterministic person identity resolution, staging, duplicate detection, and import classification. Understanding this lifecycle is essential for explaining runtime behaviors such as the `409 DUPLICATE_PROFILE` response and the `SAME_DOCUMENT` idempotent re-import classification.

## Decision

CareerOS defines the **Profile Acquisition / Import Lifecycle** with the following stages and concepts:

### 1. Profile Import Lifecycle Stages

**Document Upload**
- User uploads a CV document (DOCX, DOC, TXT) via `POST /profiles/import`.
- The document bytes are retained as the source of truth for provenance.

**Extraction**
- Document is parsed and text is extracted.
- LLM-based extraction produces structured entities (person, experiences, skills, etc.).
- Extraction produces an `extractionTimestamp` (ISO 8601) recorded in the profile.

**Deterministic Person Identity**
- The extracted person's name is resolved to a deterministic `person.id` using `person_id_from_name()` (slugified lowercase name).
- This `person.id` is the primary key for duplicate detection across the profile store.

**Staging**
- The assembled canonical profile is written to `profiles/staging/{person.id}-profile.yaml`.
- The profile carries `_acquisition` provenance: `sourceName`, `sourceHash` (SHA-256 of raw bytes), `sourceDocument`, `extractionTimestamp`, `importedAt`.
- Top-level `extensions.importedAt` mirrors `importedAt` for API compatibility.

**Duplicate Detection (File-Existence Gate)**
- Before writing, `YamlWriter` checks if `profiles/staging/{person.id}-profile.yaml` already exists.
- If the target file exists → `DuplicateProfileError` (person.id collision) → `409 DUPLICATE_PROFILE` response.
- This gate runs **before** any classification or source-hash comparison.

**Import Classification (Post-Write)**
- After a successful write, `classify_import()` compares the new profile against the existing store (staging + canonical).
- Classification produces one of:
  - `SAME_DOCUMENT` — exact `sourceHash` match with an existing record.
  - `POSSIBLE_SAME_PERSON` — deterministic identity signals match (name, email, phone, LinkedIn, GitHub, name-token containment).
  - `IDENTITY_CONFLICT` — strong name signal with a conflicting present-but-different email or phone.
  - `NEW_PERSON` — no matches.

**Reconciliation / Promotion (Future)**
- Human review and explicit reconciliation are required before a staging profile is promoted to canonical or merged with an existing profile.
- No automatic merge, promotion, archive, or deletion occurs in Phase 2A/2B.

### 2. Person Identity vs Document Identity

- **Person Identity** answers: "Is this probably the same human?"  
  Determined by deterministic signals: exact email/phone/LinkedIn/GitHub, exact name slug, or conservative name-token containment (min 2 shared tokens). Produces `POSSIBLE_SAME_PERSON` or `IDENTITY_CONFLICT`.

- **Document Identity** answers: "Is this exactly the same source document?"  
  Determined by exact SHA-256 match of raw uploaded bytes (`sourceHash`). Produces `SAME_DOCUMENT`.

- These two concepts are **not equivalent**. A re-import of the same CV with a different `person.id` (e.g., legacy `person-gongora` vs deterministic `person-raul-gongora-betancourt`) will be `SAME_DOCUMENT` on hash, but the duplicate gate may block it first. Conversely, two different CVs for the same human will be `POSSIBLE_SAME_PERSON` but never `SAME_DOCUMENT`.

### 3. 409 DUPLICATE_PROFILE

The `409 DUPLICATE_PROFILE` response occurs when the resolved `person.id` already has a file at `profiles/staging/{person.id}-profile.yaml`. This can happen in three scenarios:

1. **Same `person.id`, different `sourceHash`** — a different CV for the same deterministic person was already imported.
2. **Same `person.id`, no `sourceHash` (legacy profile)** — an older staging profile (pre-Phase 2A) lacks provenance; CareerOS cannot prove it originated from the same source document.
3. **Same `person.id`, colliding record not safely provable as same document** — the existing record cannot be verified as byte-identical to the new upload.

In all three cases the existing profile is left untouched and the import returns `409`.

### 4. SAME_DOCUMENT

`SAME_DOCUMENT` is returned when:
- The new import's `person.id` matches an existing record's `person.id` (or a different `person.id` whose `_acquisition.sourceHash` matches).
- The existing record carries `_acquisition.sourceHash` **equal to** the SHA-256 of the newly uploaded document.
- The import is **idempotent**: the existing profile is returned, no new file is created, no retention occurs, the response is `201 Created` with classification `SAME_DOCUMENT`.

This applies only when the existing record was created by a Phase 2A+ import (has `sourceHash`). Legacy records without `sourceHash` can never match.

### 5. Same-Human Detection

- Different deterministic `person.id` values can represent the same real person (e.g., `person-raul-gongora` vs `person-raul-gongora-betancourt`).
- This produces a `POSSIBLE_SAME_PERSON` candidate with `matchedOn` signals (e.g., `name-tokens`, `email`, `phone`).
- **It does NOT** automatically merge, promote, archive, or delete profiles. Human/explicit reconciliation is required.

### 6. Legacy Provenance

- Older profiles (pre-Phase 2A) may not contain `_acquisition.sourceHash`.
- CareerOS therefore **cannot** retrospectively prove that a legacy profile came from the same source document as a new import.
- Such profiles remain as-is; they surface as `POSSIBLE_SAME_PERSON` candidates based on identity signals but never as `SAME_DOCUMENT`.

## Consequences

- AI agents can explain runtime behaviors (409, SAME_DOCUMENT, candidate classifications) by combining this lifecycle knowledge with runtime evidence (`sourceHash`, `person.id`, `_acquisition` fields).
- The distinction between person identity and document identity is explicit in the knowledge graph, preventing false equivalences.
- Legacy records are handled conservatively: they participate in same-human detection but never in same-document detection.
- Future reconciliation/promotion workflows will build on these deterministic classifications without altering the import gate.