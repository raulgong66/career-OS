# M1 Schema Proposal — The Professional Evidence Model

## Status

Proposal — illustrative YAML only. **No implementation.**

This document proposes the future shape of the canonical profile with a
first-class evidence model. It extends — never replaces — the current
`schemas/profile.schema.json` `evidence` definition. Anything valid today
remains valid (see `06-migration-strategy.md`).

> Notation: `+new`, `*changed`, `~derived`. Fields present in the current schema
> are unchanged in name and type.

## Future `evidence` Entity

```yaml
evidence:
  - id: "ev_2025-001"                # stable, never reused
    kind: metric                     # +new (was: free-text evidenceType)
    title: "Customer churn reduction at Acme"
    summary: "Reduced monthly customer churn from 4.8% to 3.2% over six months."
    # --- provenance (new) ---
    provenance:
      source:
        kind: document               # document | url | person | system | model
        id: "doc_resume_2025-04"
        label: "Resume submitted 2025-04"
      capturedAt: "2025-04-15T10:00:00Z"
      capturedBy: "importer:resume-v2"
    # --- confidence (new) ---
    verificationStatus: imported     # verified|observed|imported|generated|user_confirmed|estimated
    reviewState: pending_review      # draft|pending_review|approved|rejected|archived
    # --- substance (new) ---
    metrics:                         # +new measurable outcomes
      - id: "mo_2025-001-01"
        name: "Monthly customer churn"
        value: 3.2
        unit: "percent"
        period:
          start: "2024-10-01"
          end: "2025-03-31"
        target: 3.5
        sourceMetric: "ev_2025-001"
    # --- material (unchanged shape) ---
    links:
      - url: "https://github.com/example/repo"
        label: "Supporting repository"
    # --- support (unchanged shape) ---
    relatedRefs:
      - id: "exp_201"                # *type now explicit & open
        type: "experience"
      - id: "claim_003"
        type: "careerClaim"          # future element kind
    # --- lifecycle (new) ---
    history:                         # +new append-only log
      - at: "2025-04-15T10:00:00Z"
        event: "created"
        detail: "created by importer:resume-v2"
      - at: "2025-04-16T08:00:00Z"
        event: "status_changed"
        detail: "imported -> pending_review"
    # --- extension (unchanged shape) ---
    extensions: {}
```

## Future Element `evidenceRefs`

Reference shape is unchanged from today (`id` + `type`); only the allowed set
of types grows.

```yaml
experience:
  id: "exp_201"
  title: "Senior Platform Engineer"
  evidenceRefs:                       # unchanged shape
    - id: "ev_2025-001"
      type: "evidence"
  # ...
```

## New: Career Claim (future element)

```yaml
careerClaims:
  - id: "claim_003"
    statement: "Reduced customer churn by ~30% at Acme."
    kind: quantified_outcome          # quantified_outcome | responsibility | leadership | ... (open)
    date: "2025-03-31"
    evidenceRefs:
      - id: "ev_2025-001"
        type: "evidence"
```

## Complete Field Catalog

### Evidence fields

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | string | no | — | stable identity |
| `kind` | enum | no | `document` | evidence kinds (R1.2) |
| `title` | string | no | — | human-readable |
| `summary` | string | yes | — | what the evidence supports |
| `provenance.source` | object | yes | — | origin record |
| `provenance.capturedAt` | datetime | yes | — | capture time |
| `provenance.capturedBy` | string | yes | — | actor/agent/system |
| `verificationStatus` | enum | no | `generated` | confidence input (R3.1) |
| `reviewState` | enum | no | `draft` | lifecycle (R1.5) |
| `metrics[]` | array | yes | — | measurable outcomes |
| `links[]` | array | yes | — | URLs / files (unchanged) |
| `relatedRefs[]` | array | yes | — | supported elements (unchanged shape) |
| `history[]` | array | yes | — | append-only change log |
| `extensions` | object | yes | — | controlled extension point (unchanged) |

### Evidence kind enum (R1.2)

`achievement | project | certification | publication | presentation |
customer_feedback | recommendation | metric | kpi | award |
github_repository | production_deployment | architecture_document |
oss_contribution | document`

### Verification status enum (R3.1)

`verified | observed | imported | generated | user_confirmed | estimated`

### Review state enum (R1.5)

`draft | pending_review | approved | rejected | archived`

### Provenance source kind enum

`document | url | person | system | model`

## Consistency Rules (validated by a future validator, not the schema)

1. `relatedRefs` agrees with the union of `evidenceRefs` pointing at the item.
2. `history` is append-only; status changes append `status_changed` events.
3. `estimated` evidence may not be referenced by an approved recruiter-facing
   artifact without an explicit reasoning-layer override.
4. Canonical identity is computable from `kind + normalized(title) + source +
   date(window)` — never from `id`.
