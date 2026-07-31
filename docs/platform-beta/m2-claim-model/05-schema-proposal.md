# M2 Schema Proposal — The Professional Claim Model

## Status

Proposal — illustrative YAML only. **No implementation. No migration.**

The claim schema is a **new, separate** layer. It does not modify
`schemas/profile.schema.json`, does not alter ADR-002's evidence contract, and
is not written to any file. It is the target shape for the claim layer when
implementation begins.

> Notation: fields marked `(ADR-002)` reuse the reference contract and evidence
> semantics from the Evidence Model.

## Future `claims` Collection

```yaml
claims:
  - id: "claim_003"
    title: "Reduced deployment time by 60%"
    statement: "I reduced production deployment time by 60% by automating release pipelines."
    category: quantified_outcome      # quantified_outcome | responsibility | leadership | technical_skill | achievement | education | certification | product_built | career_direction (open)
    # --- assertion (inputs only, never computed scores) ---
    strength: strong                  # weak | supported | strong | exceptional (qualitative)
    confidence:                       # inputs only — aggregates ADR-002 verificationStatus
      evidenceStatuses: [imported, verified]
      reviewState: approved
      measurableOutcomes: true
    # --- support (ADR-002 refs) ---
    evidenceRefs:
      - id: "ev_2025-002"
        type: "evidence"             # unchanged ref shape from ADR-002
      - id: "ev_2025-007"
        type: "evidence"
    # --- anchoring ---
    skillRefs:
      - id: "skl_310"
        type: "skill"
    experienceRefs:
      - id: "exp_201"
        type: "experience"
    # --- deployment ---
    targetContexts:
      - cv
      - linkedin
      - biography
      - interview_answers
      - technical_profile
    priority: 10                      # higher = more prominent within a context
    visibility: public                # public | private | internal
    # --- governance ---
    status: approved                  # draft | generated | reviewed | approved | deprecated | archived
    owner: "prof_marachen"
    tags: ["kubernetes", "delivery", "automation"]
    history:                          # append-only
      - { at: "2025-05-10T09:00:00Z", from: "generated", to: "reviewed", actor: "reviewer:r_02", reason: "review requested" }
      - { at: "2025-05-11T14:30:00Z", from: "reviewed", to: "approved", actor: "reviewer:r_02", reason: "evidence verified" }
    extensions: {}
```

## Field Catalog

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `id` | string | no | — | stable identity |
| `title` | string | no | — | short label |
| `statement` | string | no | — | the claim, in professional language |
| `category` | string (open enum) | no | `achievement` | classifies the claim |
| `strength` | enum | yes | — | `weak | supported | strong | exceptional`; qualitative |
| `confidence` | object | yes | — | inputs only; no score |
| `evidenceRefs` | array | yes | `[]` | ADR-002 refs; may be empty (weak claim) |
| `skillRefs` | array | yes | `[]` | refs to skill elements |
| `experienceRefs` | array | yes | `[]` | refs to experience elements |
| `targetContexts` | array (enum) | yes | `[cv]` | eligibility set |
| `priority` | integer | yes | `0` | relative prominence |
| `visibility` | enum | no | `internal` | `public | private | internal` |
| `status` | enum | no | `draft` | lifecycle state (04) |
| `owner` | string | yes | profile id | responsible party |
| `tags` | array | yes | `[]` | free-form labels |
| `history` | array | yes | `[]` | append-only lifecycle log |
| `extensions` | object | yes | `{}` | controlled extension point |

### Category enum (open)

`quantified_outcome | responsibility | leadership | technical_skill |
achievement | education | certification | product_built | career_direction`

### Strength enum (qualitative, not scored)

`weak | supported | strong | exceptional`

### Status enum (lifecycle)

`draft | generated | reviewed | approved | deprecated | archived`

### Target context enum (open)

`professional_summary | experience | executive_profile | cv | linkedin |
biography | interview_answers | portfolio | presentation`

### Visibility enum

`public | private | internal`

## Selection View: Claim within a Target Context

For a given document, claims are selected and ordered by the Reasoning Engine
(ADR-0005). The model exposes the inputs:

```yaml
targetContextSelection:
  context: cv
  selectedClaims: ["claim_003", "claim_001"]
  orderedBy:      # described inputs, not a score
    - strength
    - priority
    - relevanceToContext
    - ownerOverride
```

## Consistency Rules (validated by a future validator)

1. `status` transitions follow `04-claim-lifecycle.md`; every transition is
   appended to `history`.
2. `strength` and `confidence` are **inputs/levels only** — never computed at
   read time in this milestone.
3. `evidenceRefs` reuse the ADR-002 `{ id, type }` shape; an evidence item's
   `relatedRefs` (ADR-002) should eventually agree with the union of claim
   `evidenceRefs`.
4. `generated` claims are not selectable for output without an explicit
   reasoning-layer override.
5. Internal fields (`status`, `confidence`, `visibility: internal`) never
   render into recruiter-facing output (NFR-5).
