# M2 Domain Model — The Professional Claim Model

## Status

Proposal — architecture only. No implementation.

## Overview

The domain model defines the entities and relationships of the claim layer — the
semantic bridge between **Evidence** (ADR-002, *"How do we know?"*) and
**recruiter-facing documents** (*"What are we saying?"*).

## Major Entities

### Claim

A discrete, typed, human-readable statement asserted about the professional.
The unit every document section, recommendation, and interview answer draws
from.

```
Claim
├── identity      id, title, statement, category
├── assertion     confidence (inputs), strength (level)
├── support       evidenceRefs → Evidence (ADR-002)
├── anchoring     skillRefs, experienceRefs → profile elements
├── deployment    targetContexts, priority, visibility
├── governance    status, owner, tags, history
└── extensions    controlled extension point
```

| Field group | Purpose |
|---|---|
| `id` | Stable identity; never reused across claims |
| `title` | Short label (e.g. "Reduced deployment time 60%") |
| `statement` | The claim itself, in professional language |
| `category` | Type of claim (see Claim Category) |
| `confidence` | *Inputs only* — aggregates the verification status of supporting evidence (ADR-002) |
| `strength` | Qualitative level: `weak | supported | strong | exceptional` |
| `evidenceRefs` | The evidence items that support this claim |
| `skillRefs`, `experienceRefs` | Profile elements the claim is anchored to |
| `targetContexts` | Where the claim is eligible to appear |
| `priority` | Relative prominence within a context |
| `visibility` | Public/private/internal exposure of the claim |
| `status` | Lifecycle state (see 04-claim-lifecycle) |
| `owner` | Who is responsible for the claim (defaults to the professional) |
| `history` | Append-only log of state changes and edits |

### Claim Category

An open enumeration that classifies what kind of statement a claim is.
Illustrative starting set:

`quantified_outcome | responsibility | leadership | technical_skill |
achievement | education | certification | product_built | career_direction`

Open by design so new categories are additive (NFR-4).

### Strength Level

Qualitative, ordered levels: `weak < supported < strong < exceptional`.
The model stores the level and the **inputs** strength will be derived from; it
does not compute a score (R5.2).

### Target Context

An open enumeration of recruiter-facing artifacts:

`professional_summary | experience | executive_profile | cv | linkedin |
biography | interview_answers | portfolio | presentation`

### Evidence (from ADR-002, referenced, unchanged)

The supporting records a claim rests on. Claims reference evidence; they never
duplicate it.

### Reference

`{ id, type }` — the exact shape established in ADR-002. Reused for
`evidenceRefs`, `skillRefs`, and `experienceRefs` so any current or future
element kind can be referenced.

## Relationship Model

```
                ┌─────────────────────────────┐
                │         Evidence            │   ADR-002
                │  "How do we know?"          │
                └──────────────┬──────────────┘
                               │ supports (many-to-many)
                               ▼
                ┌─────────────────────────────┐
                │           Claim             │   this model
                │   "What are we saying?"     │
                └──────┬──────────────┬───────┘
        skillRefs/     │              │ targetContexts
        experienceRefs │              ▼
                ┌──────┴────────┐   ┌──────────────────────────┐
                │ Profile       │   │ Target Contexts          │
                │ elements      │   │ CV, LinkedIn, Biography, │
                │ (canonical)   │   │ Executive Profile,       │
                └───────────────┘   │ Interview Answers,       │
                                    │ Portfolio, Presentation, │
                                    │ Professional Summary     │
                                    └────────────┬─────────────┘
                                                 ▼
                                    ┌──────────────────────────┐
                                    │         Document         │
                                    └──────────────────────────┘
```

### supports (Evidence → Claim), many-to-many

- A claim references **0..n** evidence items.
- An evidence item supports **0..n** claims.
- Direction of meaning: *evidence supports claim*. Claim `evidenceRefs` is the
  navigable edge; evidence `relatedRefs` (ADR-002) is the derived reverse index.

### used by (Claim → Target Context), many-to-many

- A claim may be used in **0..n** target contexts.
- A target context draws from **0..n** claims.
- `targetContexts` expresses *eligibility*; selection and ordering for a
  specific document is a reasoning concern (ADR-0005), not a model concern.

### anchored to (Claim → Profile Element)

- `skillRefs` and `experienceRefs` bind a claim to the canonical profile
  elements it relates to. Purely navigational; elements do not need a back-ref.

## Claim Confidence (inputs only)

A claim's confidence is an **aggregate of ADR-002 evidence inputs**:

```
Claim confidence ← composed of
├── verificationStatus of each supporting evidence item (ADR-002)
├── strength of the evidence set (volume, measurable outcomes, recency)
├── claim reviewState (approved > generated > draft)
└── priority/visibility decisions by the owner
```

No score is stored or computed. The Reasoning Engine (M3) may derive an
aggregate using these inputs; this model only fixes which inputs exist.

## Claim Strength (qualitative derivation inputs)

Strength is a qualitative level that should eventually be derived from:

| Input | Source | Weighted direction |
|---|---|---|
| Number of supporting evidence items | claim.evidenceRefs | more → stronger |
| Verification status mix | evidence.verificationStatus (ADR-002) | `verified`/`observed` > `imported` > `estimated` |
| Measurable outcomes present | evidence.metrics (ADR-002) | quantified → stronger |
| Recency of supporting evidence | evidence.provenance.capturedAt | recent → stronger |
| Review approval | claim.status | `approved` > `reviewed` > `generated` |
| Reuse across contexts | claim.targetContexts + document usage | broader verified use → stronger |

These are **inputs**, not an algorithm. `weak | supported | strong |
exceptional` is the qualitative ladder those inputs should eventually map onto.

## Explainability Model

The reasoning engine explains a claim deterministically:

```
Recommendation
  └─ references ─▶ Claim (id, statement, status)
        └─ supported by ─▶ Evidence items (id, verificationStatus)
              └─ produced by ─▶ Reasoning Rule (deterministic, ADR-0005)
```

- **Recommendations reference claims, not raw elements** (R6.2). Where a claim
  does not yet exist for a statement, the recommendation should say so
  explicitly (e.g. *"no claim covers this experience"*).
- Explanations are reproducible from the graph and rules alone — no model
  output required (ADR-0005 constraint).

## Entity Summary

| Entity | Kind of thing | Origin |
|---|---|---|
| Claim | core (this model) | first-class statement |
| Claim Category | value (open enum) | classifies claims |
| Strength Level | value (enum) | qualitative, not scored |
| Target Context | value (open enum) | eligibility of a claim |
| Evidence | referenced | ADR-002, unchanged |
| Reference | value | `{ id, type }`, ADR-002 shape |
| Claim History | value | append-only lifecycle log |
