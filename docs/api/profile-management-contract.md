# Profile Management API Contract

> **Status for v0.2.0-platform-alpha**: The four core endpoints (`POST /profiles/import`, `GET /profiles`, `GET /profiles/{id}`, `DELETE /profiles/{id}`) are implemented. Notable gaps vs. this contract: duplicate detection (Section 5.5), `filename` override parameter (Section 2.1), and `VALIDATION_ERROR` error code are not yet implemented. Legacy endpoints do not use the `ApiErrorResponse` format. See Phase 7 validation report for full details.

## Section 1 — Workflow

### User Journey

```
User opens "My Profiles" page
         │
         ├─ [Existing profiles listed] ─→ User selects a profile → Tailoring
         │
         └─ [No profiles / wants new one]
                │
                User clicks "Import CV"
                │
                File picker opens (.docx)
                │
                File uploaded to POST /profiles/import
                │
                Backend runs AcquisitionPipeline:
                  read → extract → LLM extract → normalize → build → validate → persist
                │
                Backend returns ImportResponse (profile id + summary)
                │
                Frontend navigates to profile detail page
                │
                Profile available in list (GET /profiles)
                │
                User opens profile detail (GET /profiles/{id})
                │
                Profile used for tailoring (/generate/artifact)
                │
                Artifacts generated
```

### States

| State | Description |
|---|---|
| Empty state | No profiles exist. Frontend shows "Import your first CV" CTA. |
| Importing | File uploading. Backend processing. Spinner shown. |
| Import complete | Profile appears in list with name and artifact count. |
| Import failed | Error banner with reason. Retry option. |
| Profile detail | Full profile viewed. Artifacts listed. Navigate to tailoring. |

---

## Section 2 — REST Endpoints

### 2.1 `POST /profiles/import`

Import a CV document and create a canonical profile.

| Property | Value |
|---|---|
| **HTTP Method** | `POST` |
| **URL** | `/profiles/import` |
| **Content-Type** | `multipart/form-data` |
| **Purpose** | Upload a CV document (DOCX), run the acquisition pipeline, persist the resulting canonical profile, and return a frontend-friendly summary. |

**Request:**

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | `binary` | Yes | CV document file. See accepted types below. |
| `filename` | `string` | No | Override filename (defaults to upload filename). |

**Response `201 Created`:**

```json
{
  "profileId": "raul-gongora-profile",
  "profile": {
    "id": "raul-gongora-profile",
    "name": "Raul Gongora Betancourt",
    "headline": "Senior IT DevSecOps Specialist & AI Solutions Architect",
    "artifactCount": 2,
    "artifactIds": ["cv-english-source", "cover-letter-devsecops-ai"],
    "importedAt": "2026-07-29T12:00:00Z"
  }
}
```

**Response `400 Bad Request`:**

```json
{
  "error": "INVALID_FILE",
  "detail": "Unsupported file type: .pdf. Accepted types: .docx"
}
```

**Response `422 Unprocessable Entity`:**

```json
{
  "error": "IMPORT_FAILED",
  "detail": "LLM extraction returned no person data. The document may not contain a CV.",
  "processingErrors": [
    "No person name found in extracted text"
  ]
}
```

**Response `409 Conflict`:**

```json
{
  "error": "DUPLICATE_PROFILE",
  "detail": "A profile with the same name already exists: Raul Gongora Betancourt",
  "existingProfileId": "raul-gongora-profile"
}
```

**Status codes:**

| Code | Condition |
|---|---|
| `201` | Profile created successfully. |
| `400` | Invalid or unsupported file. |
| `409` | Duplicate profile detected (same person name). |
| `422` | Import pipeline failed (LLM extraction, validation, etc.). |
| `500` | Internal server error. |

---

### 2.2 `GET /profiles`

List all available profiles.

| Property | Value |
|---|---|
| **HTTP Method** | `GET` |
| **URL** | `/profiles` |
| **Purpose** | Return metadata for all imported profiles for list display and selection. |

**Request:** None.

**Response `200 OK`:**

```json
[
  {
    "id": "raul-gongora-profile",
    "name": "Raul Gongora Betancourt",
    "headline": "Senior IT DevSecOps Specialist & AI Solutions Architect",
    "artifactCount": 2,
    "artifactIds": [
      "cv-english-source",
      "cover-letter-devsecops-ai"
    ],
    "importedAt": "2026-07-29T12:00:00Z"
  }
]
```

**Status codes:**

| Code | Condition |
|---|---|
| `200` | Success. Returns array (may be empty). |

---

### 2.3 `GET /profiles/{id}`

Get full profile detail.

| Property | Value |
|---|---|
| **HTTP Method** | `GET` |
| **URL** | `/profiles/{id}` |
| **Purpose** | Return the complete frontend-oriented profile DTO for display and editing. |

**Path parameters:**

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Profile identifier (e.g., `raul-gongora-profile`). |

**Response `200 OK`:**

```json
{
  "id": "raul-gongora-profile",
  "person": {
    "firstName": "Raul",
    "lastName": "Gongora Betancourt",
    "headline": "Senior IT DevSecOps Specialist & AI Solutions Architect",
    "city": "Stockholm",
    "country": "Sweden",
    "languages": [
      { "name": "Swedish", "proficiency": "fluent" },
      { "name": "English", "proficiency": "fluent" }
    ]
  },
  "artifacts": [
    {
      "id": "cv-english-source",
      "type": "CV",
      "name": "Raul Gongora English CV",
      "sourceCount": 22
    },
    {
      "id": "cover-letter-devsecops-ai",
      "type": "COVER_LETTER",
      "name": "DevSecOps and AI Solutions Cover Letter",
      "sourceCount": 9
    }
  ],
  "summary": "Results-driven senior IT DevSecOps specialist and cloud architect with 12+ years of experience managing, scaling, and securing mission-critical enterprise systems.",
  "importedAt": "2026-07-29T12:00:00Z"
}
```

**Response `404 Not Found`:**

```json
{
  "error": "NOT_FOUND",
  "detail": "Profile not found: non-existent-id"
}
```

**Status codes:**

| Code | Condition |
|---|---|
| `200` | Profile found and returned. |
| `404` | Profile id does not exist. |

---

### 2.4 `DELETE /profiles/{id}`

Delete a profile and its artifacts.

| Property | Value |
|---|---|
| **HTTP Method** | `DELETE` |
| **URL** | `/profiles/{id}` |
| **Purpose** | Remove a profile and all its associated data from storage. |

**Path parameters:**

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Profile identifier. |

**Response `204 No Content`:** No body.

**Response `404 Not Found`:**

```json
{
  "error": "NOT_FOUND",
  "detail": "Profile not found: non-existent-id"
}
```

**Status codes:**

| Code | Condition |
|---|---|
| `204` | Profile deleted successfully. |
| `404` | Profile id does not exist. |
| `500` | Deletion failed (filesystem error). |

---

## Section 3 — DTOs

### 3.1 `ProfileSummary`

Used in `GET /profiles` list response.

```json
{
  "id": "raul-gongora-profile",
  "name": "Raul Gongora Betancourt",
  "headline": "Senior IT DevSecOps Specialist & AI Solutions Architect",
  "artifactCount": 2,
  "artifactIds": ["cv-english-source", "cover-letter-devsecops-ai"],
  "importedAt": "2026-07-29T12:00:00Z"
}
```

| Field | Type | Description | Mapped from canonical |
|---|---|---|---|
| `id` | `string` | Profile identifier (lowercase, hyphenated, derived from person name). | `person.id` or generated from name |
| `name` | `string` | Full name of the person. | `person.names[0].value` |
| `headline` | `string` | Professional headline. | `person.positioning.headline` |
| `artifactCount` | `integer` | Number of artifacts in the profile. | `artifacts.length` |
| `artifactIds` | `string[]` | IDs of all artifacts. | `artifacts[].id` |
| `importedAt` | `string` (ISO 8601) | When the profile was imported. | `extensions.importedAt` or filesystem timestamp |

### 3.2 `ProfileDetails`

Used in `GET /profiles/{id}` response.

```json
{
  "id": "raul-gongora-profile",
  "person": {
    "firstName": "Raul",
    "lastName": "Gongora Betancourt",
    "headline": "Senior IT DevSecOps Specialist & AI Solutions Architect",
    "city": "Stockholm",
    "country": "Sweden",
    "languages": [
      { "name": "Swedish", "proficiency": "fluent" },
      { "name": "English", "proficiency": "fluent" }
    ]
  },
  "artifacts": [
    {
      "id": "cv-english-source",
      "type": "CV",
      "name": "Raul Gongora English CV",
      "sourceCount": 22
    }
  ],
  "summary": "Results-driven senior IT DevSecOps specialist...",
  "importedAt": "2026-07-29T12:00:00Z"
}
```

| Field | Type | Description | Mapped from canonical |
|---|---|---|---|
| `id` | `string` | Profile identifier. | `person.id` or derived |
| `person.firstName` | `string` | First/given name. | First token of `person.names[0].value` |
| `person.lastName` | `string` | Last/family name. | Remainder of `person.names[0].value` after first token |
| `person.headline` | `string` | Professional headline. | `person.positioning.headline` |
| `person.city` | `string \| null` | City. | `person.location.city` |
| `person.country` | `string \| null` | Country. | `person.location.country` |
| `person.languages` | `array` | Languages spoken. | `person.languages` |
| `artifacts[].id` | `string` | Artifact ID. | `artifacts[].id` |
| `artifacts[].type` | `string` | Artifact type (CV, COVER_LETTER). | `artifacts[].artifactType` |
| `artifacts[].name` | `string` | Artifact display name. | `artifacts[].title` |
| `artifacts[].sourceCount` | `integer` | Number of source refs. | `artifacts[].sourceRefs.length` |
| `summary` | `string \| null` | First professional summary text. | `professionalSummaries[0].text` |
| `importedAt` | `string` (ISO 8601) | Import timestamp. | `extensions.importedAt` |

### 3.3 `ImportResponse`

Returned from `POST /profiles/import` on success.

```json
{
  "profileId": "raul-gongora-profile",
  "profile": {
    "id": "raul-gongora-profile",
    "name": "Raul Gongora Betancourt",
    "headline": "Senior IT DevSecOps Specialist & AI Solutions Architect",
    "artifactCount": 2,
    "artifactIds": ["cv-english-source", "cover-letter-devsecops-ai"],
    "importedAt": "2026-07-29T12:00:00Z"
  }
}
```

The response wraps the `ProfileSummary` in a `{ profileId, profile }` envelope. This allows the frontend to navigate directly to the imported profile without an additional `GET /profiles/{id}` request.

### 3.4 `ApiError`

Consistent error format used across all endpoints.

```json
{
  "error": "NOT_FOUND",
  "detail": "Profile not found: non-existent-id",
  "processingErrors": null
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `error` | `string` | Yes | Machine-readable error code (SCREAMING_SNAKE_CASE). |
| `detail` | `string` | Yes | Human-readable description. |
| `processingErrors` | `string[] \| null` | No | Optional list of specific processing errors (used in import failures). |

**Standard error codes:**

| Code | HTTP Status | Meaning |
|---|---|---|
| `INVALID_FILE` | 400 | Unsupported file type, empty file, etc. |
| `FILE_TOO_LARGE` | 400 | Exceeds maximum file size. |
| `DUPLICATE_PROFILE` | 409 | Profile with same person name already exists. |
| `NOT_FOUND` | 404 | Requested resource does not exist. |
| `IMPORT_FAILED` | 422 | Acquisition pipeline could not extract a valid profile. |
| `VALIDATION_ERROR` | 422 | Generated profile failed schema validation. |
| `INTERNAL_ERROR` | 500 | Unexpected server error. |

---

## Section 4 — Canonical Mapping

The canonical profile schema (`schemas/profile.schema.json`) is the source of truth. DTOs are frontend-oriented projections. All mapping logic lives in the API layer.

### 4.1 Person Name

**Frontend DTO:**
```json
{
  "firstName": "Raul",
  "lastName": "Gongora Betancourt"
}
```

**Canonical source:**
```yaml
person:
  names:
    - value: "Raul Gongora Betancourt"
      usage: professional
```

**Mapping rule:**

The API exposes `firstName` and `lastName` for frontend compatibility. The mapping strategy is an implementation detail of the API layer and may evolve without changing the public contract. The canonical schema remains unchanged.

### 4.2 Artifact Type

**Frontend DTO:**
```json
{
  "type": "CV"
}
```

**Canonical source:**
```yaml
artifacts:
  - artifactType: "CV"
```

**Mapping rule:**
```
artifactType → type (direct copy)
```

### 4.3 Artifact Count

**Frontend DTO:**
```json
{
  "artifactCount": 2
}
```

**Canonical source:**
```yaml
artifacts:
  - id: cv-english-source
  - id: cover-letter-devsecops-ai
```

**Mapping rule:**
```
len(artifacts) → artifactCount
```

### 4.4 Headline

**Frontend DTO:**
```json
{
  "headline": "Senior IT DevSecOps Specialist & AI Solutions Architect"
}
```

**Canonical source:**
```yaml
person:
  positioning:
    headline: "Senior IT DevSecOps Specialist & AI Solutions Architect"
```

**Mapping rule:**
```
person.positioning.headline → headline
```

### 4.5 Summary

**Frontend DTO:**
```json
{
  "summary": "Results-driven senior IT DevSecOps specialist..."
}
```

**Canonical source:**
```yaml
professionalSummaries:
  - id: summary-professional-profile
    text: "Results-driven senior IT DevSecOps specialist..."
```

**Mapping rule:**
```
professionalSummaries[0].text → summary (null if empty)
```

### 4.6 Location

**Frontend DTO:**
```json
{
  "city": "Stockholm",
  "country": "Sweden"
}
```

**Canonical source:**
```yaml
person:
  location:
    city: Stockholm
    country: Sweden
```

**Mapping rule:**
```
person.location.city     → city
person.location.country  → country
```

### 4.7 Source Count

**Frontend DTO:**
```json
{
  "sourceCount": 22
}
```

**Canonical source:**
```yaml
artifacts:
  - sourceRefs:
      - id: ...
      - id: ...
```

**Mapping rule:**
```
len(artifacts[].sourceRefs) → sourceCount
```

### 4.8 Import Timestamp

**Frontend DTO:**
```json
{
  "importedAt": "2026-07-29T12:00:00Z"
}
```

**Canonical source:**
```yaml
extensions:
  importedAt: "2026-07-29T12:00:00Z"
```

**Mapping rule:**
```
extensions.importedAt → importedAt
```

If `extensions.importedAt` is absent, fall back to the file creation time or the ISO timestamp of the import request.

### 4.9 Profile ID

**Frontend DTO:**
```json
{
  "id": "raul-gongora-profile"
}
```

**Canonical source:**
```yaml
person:
  id: person-raul-gongora
```

**Mapping rule:**
The API DTO `id` is the canonical profile filename (without extension), e.g. `raul-gongora-profile`. The canonical `person.id` is an internal identifier (`person-raul-gongora`). The API layer resolves the profile by filename, not by the internal person id.

---

## Section 5 — Upload Design

### 5.1 Transport

- **Content-Type:** `multipart/form-data`
- **Single field:** `file` containing the binary document.
- Backend receives the file, saves it to a temporary location, runs `AcquisitionPipeline.run()` with the temp path, then deletes the temp file.
- The pipeline writes the resulting profile to `profiles/{id}.yaml`.

### 5.2 Accepted File Types

| Format | MIME Type | Supported |
|---|---|---|
| DOCX | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | Yes |
| DOC | `application/msword` | Yes (via DocumentReader) |
| TXT | `text/plain` | TBD — check DocumentReader support |

The `DocumentReader` in `careeros/acquisition/document_reader.py` determines the actual parseable formats.

### 5.3 Maximum File Size

**Recommendation: 10 MB.**

Rationale:
- CV documents rarely exceed 1-2 MB.
- The acquisition pipeline parses the full document into memory.
- 10 MB provides generous headroom while preventing resource exhaustion.

The backend should return `400 INVALID_FILE` if the file exceeds the limit.

### 5.4 Validation Behaviour

The import endpoint validates at two stages:

**Stage 1 — File-level validation (synchronous, before pipeline):**
- File type must be in the accepted list.
- File size must not exceed 10 MB.
- File must not be empty.

**Stage 2 — Pipeline validation (during acquisition):**
- `DocumentReader` must successfully parse the file into text.
- `LLMExtractor` must return at minimum a person name.
- `CanonicalProfileBuilder` must produce a valid canonical profile.
- `EntityValidator` must validate the profile against the canonical schema.

If Stage 2 fails, return `422 IMPORT_FAILED` with `processingErrors` detailing what went wrong.

### 5.5 Duplicate Handling

The endpoint should check whether a profile with the same person name (first + last) already exists in the `profiles/` directory.

- If a match is found, return `409 DUPLICATE_PROFILE`.
- The response includes the `existingProfileId` so the frontend can navigate to it.
- The frontend should offer: "A profile for Raul Gongora already exists. Open existing profile / Import as new?"

If the user chooses "Import as new", the frontend can retry with a query parameter `?allowDuplicate=true`, or the duplicate check can be skipped. Design choice: skip the duplicate check on retry.

### 5.6 Import Result

On successful import, return `201 Created` with an `ImportResponse` body.

The profile YAML is written to `profiles/{id}.yaml`.

The profile id is derived from the person name:
```
"Raul Gongora Betancourt"
  → lowercase + replace spaces with hyphens
  → remove non-alphanumeric except hyphens
  → "raul-gongora-betancourt"
```

If a file with that id already exists (same person imported again), the endpoint appends a suffix: `raul-gongora-betancourt-2`.

---

## Section 6 — Error Model

### 6.1 Consistent Format

All errors use the `ApiError` DTO:

```json
{
  "error": "ERROR_CODE",
  "detail": "Human-readable description",
  "processingErrors": null
}
```

### 6.2 Error Examples

**400 — Invalid file type:**
```json
{
  "error": "INVALID_FILE",
  "detail": "Unsupported file type: application/pdf. Accepted types: application/vnd.openxmlformats-officedocument.wordprocessingml.document, application/msword, text/plain"
}
```

**400 — File too large:**
```json
{
  "error": "FILE_TOO_LARGE",
  "detail": "File size 15 MB exceeds maximum of 10 MB"
}
```

**404 — Profile not found:**
```json
{
  "error": "NOT_FOUND",
  "detail": "Profile not found: non-existent-id"
}
```

**409 — Duplicate profile:**
```json
{
  "error": "DUPLICATE_PROFILE",
  "detail": "A profile with the name Raul Gongora Betancourt already exists",
  "existingProfileId": "raul-gongora-profile"
}
```

**422 — Import failed (LLM extraction):**
```json
{
  "error": "IMPORT_FAILED",
  "detail": "Could not extract a valid profile from the document",
  "processingErrors": [
    "No person name found in extracted text",
    "No skills or experience sections detected"
  ]
}
```

**422 — Validation error:**
```json
{
  "error": "VALIDATION_ERROR",
  "detail": "Generated profile failed schema validation",
  "processingErrors": [
    "person.names: field is required",
    "person.positioning.headline: field is required"
  ]
}
```

**500 — Internal error:**
```json
{
  "error": "INTERNAL_ERROR",
  "detail": "An unexpected error occurred while processing the profile"
}
```

---

## Section 7 — Frontend Compatibility

### 7.1 Services That Can Remain Unchanged

| Service | Status | Reason |
|---|---|---|
| `TailoringService` | **Unchanged** | Uses `GET /profiles` (returns `ProfileSummary[]`, compatible with existing `ProfileInfo`) and `POST /generate/artifact`. Neither changes. |
| `DocumentService` | **Unchanged** | Currently fully mocked. When wired, it will use `POST /generate/artifact` which does not change. |

### 7.2 TypeScript Interfaces That Require Modification

| Interface | Change Required | Reason |
|---|---|---|
| `Profile` | **Replace** | Current shape (`person.firstName` + `person.lastName`) is already compatible with the new DTO, but `artifacts` type changes: `Artifact.type` will now receive canonical `artifactType` values (`"CV"`, `"COVER_LETTER"`) instead of lowercase shorthand (`"cv"`, `"cover-letter"`). |
| `Artifact` | **Add `sourceCount` field** | New field returned by `GET /profiles/{id}`. |
| `Profile` | **Remove direct dependency on canonical shape** | The current `Profile` type (person with firstName/lastName) is fully compatible with the new DTO. No structural change needed. |

### 7.3 New Types Required

| Type | Purpose |
|---|---|
| `ProfileSummary` | Replaces `ProfileInfo` (backward compatible — same fields plus `headline` and `importedAt`). |
| `ImportResponse` | Returned after successful import. Same shape as `ProfileSummary`. |
| `ApiError` | Consistent error type for error handling. |
| `PersonInfo` | Normalised person DTO used in `ProfileDetails`. |
| `ArtifactInfo` | Artifact DTO used in `ProfileDetails`. |

### 7.4 API Mismatches That Disappear After Implementing This Contract

| Current Mismatch | Status After Contract |
|---|---|
| `ProfileService.uploadProfile()` is mocked, no backend endpoint exists | ✅ `POST /profiles/import` exists |
| `ProfileService.getProfile(profileId)` is mocked, no `GET /profiles/{id}` exists | ✅ `GET /profiles/{id}` exists |
| `Profile` type uses firstName/lastName but canonical has `names[].value` | ✅ API layer maps canonical to firstName/lastName |
| `Artifact.type` vs canonical `artifactType` | ✅ API layer maps canonical `artifactType` to `Artifact.type` |
| No delete profile capability | ✅ `DELETE /profiles/{id}` exists |

---

## Section 8 — Integration With Existing Platform

### 8.1 Acquisition Pipeline

```
POST /profiles/import multipart file
         │
         ▼
Temp file written to disk
         │
         ▼
AcquisitionPipeline.run(temp_path)
  ├─ DocumentReader.read()       ← parses DOCX/DOC/TXT
  ├─ TextExtractor.extract()     ← cleans text
  ├─ LLMExtractor.extract()      ← structured extraction
  ├─ CanonicalProfileBuilder     ← normalize + build
  │   ├─ normalize(result)       ← deduplicate, sort, clean
  │   └─ build(person, ...)      ← assemble canonical profile dict
  ├─ EntityValidator.validate()  ← verify against canonical schema
  └─ YamlWriter.write()          ← persist to profiles/{id}.yaml
         │
         ▼
Profile saved. ImportResponse returned.
```

The existing `AcquisitionPipeline` class (careeros/acquisition/pipeline.py) is used as-is. The API endpoint wraps it with:
- File upload handling (multipart → temp file)
- Duplicate detection (scan profiles/ directory)
- DTO mapping (canonical → frontend DTOs)
- Error translation (pipeline exceptions → ApiError)

**No changes to the AcquisitionPipeline class are required.**

### 8.2 Canonical Profile Builder

The `CanonicalProfileBuilder` is called by `AcquisitionPipeline.run()`. It produces a canonical profile dict that is written as YAML.

The API's `GET /profiles/{id}` reads the YAML from `profiles/{id}.yaml` and maps it to the frontend DTO using the rules in Section 4.

**No changes to the canonical profile builder are required.**

### 8.3 Knowledge Graph

The knowledge graph (careeros/knowledge/) is currently not integrated into any API endpoint. It is a consumer of the canonical profile.

When the knowledge graph is integrated in a later task, it will read from the same `profiles/{id}.yaml` files. The Profile Management API is a producer for the knowledge graph.

**No changes to the knowledge graph are required.**

### 8.4 Reasoning Engine

The reasoning engine (careeros/reasoning/) is a consumer of the canonical profile and knowledge graph. It is not involved in profile management.

When the reasoning engine is exposed via API in a later task, it will consume profiles produced by this endpoint.

**No changes to the reasoning engine are required.**

### 8.5 Artifact Generation

The artifact generation pipeline (`careeros/pipelines.py`) reads profiles from `profiles/{id}.yaml` via `ProfileLoader`. It does not depend on how the profile was created (manual, import, or API).

The existing `POST /generate/artifact` endpoint uses `profile_id` to resolve the profile path. This contract is unchanged.

**No changes to artifact generation are required.**

### 8.6 Architecture Summary

```
┌─────────────────────────────────────────────────────┐
│                   Profile Management API             │
│  (new endpoints in api/main.py)                      │
│                                                      │
│  POST /profiles/import ───→ AcquisitionPipeline     │
│  GET  /profiles          ───→ filesystem scan        │
│  GET  /profiles/{id}     ───→ YAML read + DTO map   │
│  DELETE /profiles/{id}   ───→ filesystem delete      │
│                                                      │
│  DTO mapping layer: canonical → frontend DTOs        │
└─────────────────────────────────────────────────────┘
         │                         │
         ▼                         ▼
┌──────────────────┐   ┌──────────────────────┐
│  profiles/*.yaml  │   │  Existing API endpoints │
│  (canonical YAML) │   │  (unchanged)            │
└──────────────────┘   │  /generate/artifact     │
         │             │  /optimize-cv           │
         ▼             └──────────────────────┘
┌──────────────────┐
│  Reasoning Engine │  (future integration)
│  Knowledge Graph  │  (future integration)
│  Tailoring        │  (future integration)
└──────────────────┘
```

---

## Section 9 — Readiness

### 9.1 Is This Contract Sufficient for PA-002?

**Yes.**

The contract covers the four core profile management operations:

| Operation | Endpoint | PA-002 Requirement |
|---|---|---|
| Import CV | `POST /profiles/import` | Users can upload their CV. |
| List profiles | `GET /profiles` | Already exists. Contract formalises the DTO. |
| View profile | `GET /profiles/{id}` | Frontend can display profile details. |
| Delete profile | `DELETE /profiles/{id}` | Users can remove unwanted profiles. |

The DTOs map cleanly to the existing frontend types. The `ProfileService` can be wired directly. The error model gives the frontend enough information to display meaningful messages.

### 9.2 Will Later Platform Alpha Tasks Require Changes to This API?

| Future Task | Will It Change This API? | Reason |
|---|---|---|
| Reasoning integration | **No** | Reasoning engine consumes profiles; it does not modify profile management endpoints. |
| Tailored cover letter | **No** | Cover letter generation uses `POST /generate/artifact`, not profile management. |
| Full tailoring workflow | **No** | Tailoring operates on artifacts within existing profiles. Profile management is a prerequisite, not a dependency. |
| Profile editing | **Maybe — `PATCH /profiles/{id}`** | Not in scope for Platform Alpha. If added later, it extends this contract. |

The Profile Management API defined here is expected to remain stable throughout Platform Alpha. No endpoint defined here needs modification for any Platform Alpha task.
