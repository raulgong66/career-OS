# M1 Domain Model — The Professional Evidence Model

## Status

Proposal — architecture only. No implementation.

## Overview

The domain model defines the entities, relationships, and semantics of
professional evidence. It is independent of storage, schema serialization, and
scoring.

## Major Entities

### Evidence

The first-class unit of proof. An evidence item is a verifiable artifact or
record that substantiates one or more professional claims.

```
Evidence
├── identity      id, kind, title, summary
├── provenance    source, capturedAt, import
├── confidence    verificationStatus, reviewState
├── substance     metrics (measurable outcomes), narrative
├── material      links (URLs, files)
├── support       relatedRefs → profile elements
└── history       immutable change log
```

| Field group | Purpose |
|---|---|
| `id` | Stable identifier; never reused across evidence items |
| `kind` | One of the evidence kinds (R1.2); distinguishes how the item is interpreted |
| `title`, `summary` | Human-readable identity of the evidence |
| `provenance` | Where the evidence came from and when it was captured |
| `verificationStatus` | `verified` / `observed` / `imported` / `generated` / `user_confirmed` / `estimated` |
| `reviewState` | `draft` / `pending_review` / `approved` / `rejected` / `archived` |
| `metrics` | Measurable outcomes with value, unit, target, period |
| `links` | URLs and file references |
| `relatedRefs` | The profile elements this evidence supports |
| `history` | Append-only log of creation, status changes, and merges |

### Measurable Outcome

A quantifiable result attached to evidence (or to an element). Distinct from
narrative claims: it always carries a value, a unit, a date or period, and
optionally a target.

```
MeasurableOutcome
├── id
├── name            e.g. "Time to first commit"
├── value           e.g. 3
├── unit            e.g. "days"
├── date            when the outcome was measured
├── period          { start, end } if the outcome spans a range
├── target          optional benchmark the outcome was measured against
└── sourceMetric    optional link to an Evidence item of kind metric/kpi
```

### Profile Elements (supported targets)

Elements that evidence can support. Current elements exist in the Alpha schema;
**Career Claim** and **Achievement** are proposed future elements.

- Experience
- Skill
- Project
- Certification
- Education
- Achievement *(proposed)*
- Professional Summary
- Career Claim *(proposed)*

### Career Claim (proposed, future)

A first-class, atomized statement a professional makes about themselves — e.g.
"led a team of five," "reduced customer churn by 12%." Unlike narrative text,
a Career Claim is a discrete, typed, dated entity that carries `evidenceRefs`.
It is the natural unit that the Reasoning Engine and recruiter-facing documents
can cite.

## Relationship Model

### supports (Evidence → Element), many-to-many

- An **element may be supported by zero to many** evidence items.
- An **evidence item may support zero to many** elements.
- Direction of meaning: *evidence supports element*. The element's
  `evidenceRefs` is the navigable edge; the evidence's `relatedRefs` is the
  reverse index.

```
Evidence ──supports──▶ Experience
              │
              ├──▶ Skill
              ├──▶ Project
              ├──▶ Certification
              ├──▶ Education
              ├──▶ Achievement (future)
              ├──▶ Professional Summary
              └──▶ Career Claim (future)
```

**Consistency rule.** `relatedRefs` is derived from the union of `evidenceRefs`
across elements; a validation layer (not a migration) enforces agreement. The
direction of authority is *element → evidence*.

**Reference identity.** A reference carries `{ id, type }`. `type` is the
profile-element kind so evidence can point at future element types without
schema changes (R2.5).

**Orphan rule.** Evidence with no `relatedRefs` is valid and preserved (R2.4);
it becomes actionable through the `evidence_exists_but_unused` recommendation.

## Confidence Model

Confidence is a **derived concept with stored inputs**. The model stores the
inputs; it does not compute a number.

```
Confidence ← composed of
├── verificationStatus   (stored on evidence; R3.1)
├── provenanceReliability (stored source kind: registry / document / url / person / system / model)
├── recency               (capturedAt / date relative to now — derived)
├── completeness          (presence of metrics, links, period — derived)
└── reviewState           (stored human-review state)
```

- `verificationStatus` and `reviewState` are **stored**.
- `provenanceReliability` is a stored enumeration that records how trustworthy
  the source *kind* is, without assigning scores.
- `recency` and `completeness` are **derived** fields consumed later by the
  scoring layer (M3/M4). No scoring function is defined in this milestone.

### Status semantics

| Status | Semantics |
|---|---|
| `verified` | Confirmed by an independent party or registry |
| `observed` | Directly witnessed during capture (deployment, presentation, live system) |
| `imported` | Extracted from a source document (e.g. a resume) |
| `generated` | Produced by a machine (extractor, agent, reasoning engine) |
| `user_confirmed` | The professional explicitly confirmed the evidence |
| `estimated` | Inferred; no direct source exists; must be flagged |

`estimated` is the only status that carries an explicit warning obligation:
items in this state must never be presented to a recruiter as factual without
disclosure in the reasoning layer.

## Traceability Model

The **Statement Trace Path** makes every recruiter-facing statement resolvable
to a source:

```
Recruiter-facing statement (artifact text)
  ─ sourceRef ─▶ Profile element (experience, skill, project, career claim …)
  ─ evidenceRefs ─▶ Evidence item(s)
  ─ provenance ─▶ Source (document / URL / person / system) + capturedAt
```

Rules:

1. **Artifacts cite elements, not evidence.** Generated documents carry the
   `sourceRef` of the element whose text they render. Evidence references never
   appear in recruiter-facing output (R4.3, NFR-5).
2. **Elements cite evidence.** An element lists its supporting evidence via
   `evidenceRefs`.
3. **Evidence cites its source.** Provenance records origin and capture time.
4. **The path is read-only downstream.** Reasoning and generation consume;
   only acquisition writes.

### Privacy boundary

```
┌──────────────────────── knowledge layer ────────────────────────┐
│ element → evidenceRefs → evidence → verificationStatus          │
│                                    provenance                    │
│                                    reasoning notes               │
└──────────────────────────────────────────────────────────────────┘
                        │ only element text crosses
                        ▼
┌────────────────────── render layer ─────────────────────────────┐
│ recruiter-facing statement (element sourceRef only)             │
└──────────────────────────────────────────────────────────────────┘
```

## Recommendation Engine Model

The Reasoning Layer (ADR 0005) will consume the evidence model to emit
findings. The model must enable these conditions; the exact rules are out of
scope for M1.

### Condition catalog

| Condition | Detection signal (from model) | Example explanation |
|---|---|---|
| `strong_claim_without_evidence` | element asserted high-impact (e.g. metrics) but `evidenceRefs` empty | "This claim states a 40% reduction with no supporting evidence." |
| `evidence_exists_but_unused` | evidence with `relatedRefs` that is absent from every generated artifact's element set | "Evidence X never appears in any output." |
| `experience_unsupported` | experience element with zero evidence refs and no measurable outcomes | "This experience is not substantiated." |
| `duplicate_evidence` | two evidence items sharing a canonical identity or fingerprint | "Evidence A and B represent the same fact." |
| `missing_measurable_outcomes` | element claims outcomes in prose but no `metrics` present | "A quantified outcome is implied but not recorded." |

Each finding references: the element id, the evidence ids involved, their
`verificationStatus`, and a deterministic rationale — satisfying the
explainability requirement (R7.1, R7.2) without invoking any model.

## Acquisition Model

### First import (resume → evidence)

```
Resume document
  → extractor identifies claims (projects, roles, skills, metrics)
  → for each claim: create Evidence { kind, title, summary, metrics,
      verificationStatus: imported, provenance: { source: <resume>, capturedAt } }
  → create/attach profile elements with evidenceRefs to the new evidence
```

Imported evidence is always `imported` regardless of extractor type. A
subsequent human review or registry check can promote it to `verified`,
`observed`, or `user_confirmed`.

### Incremental import (merge, not duplicate)

1. **Canonical identity.** Each evidence item derives a canonical identity from
   normalized fields: `kind + normalized(title) + source + date(window)`.
   Optionally augmented by a content fingerprint (hash of normalized text +
   metrics).
2. **Match.** An incoming item is matched against existing items by canonical
   identity (exact) or fingerprint similarity (fuzzy). Matching never runs on
   `id`.
3. **Merge.** On match, the existing item gains the new `relatedRefs`; the new
   provenance reference is appended to `provenance.history`. No new item is
   created.
4. **Conflict.** If matched items disagree on facts (value, dates), both
   variants are preserved and a conflict marker is set → `pending_review`.
   Nothing is overwritten silently (R6.3).

### Deduplication invariant

The model guarantees, at the identity level, that one fact = at most one
evidence item. This is what makes `duplicate_evidence` detectable and what
enables the Reasoning Layer to reason over a clean set.

## Explainability Model

An **Explanation** is a deterministic, structured object emitted alongside any
recommendation:

```
Explanation
├── recommendationId / ruleId
├── elementId (the element the recommendation concerns)
├── evidenceIds (each supporting evidence item, with verificationStatus)
├── rationale (deterministic text built from model fields)
└── conditions (which condition catalog entries apply)
```

Because the Evidence Package (ADR 0005) is composed of pre-computed findings,
every explanation is reproducible from the graph and rules alone — no AI
generation required.

## Entity Summary

| Entity | Kind of thing | Notes |
|---|---|---|
| Evidence | core | first-class proof entity |
| MeasurableOutcome | core | quantified result |
| Career Claim | future element | atomized, typed statement |
| Profile Elements | existing/future | Experience, Skill, Project, Certification, Education, Achievement, Professional Summary, Career Claim |
| Reference | edge | `{ id, type }`, used both directions |
| Source (provenance) | value | document / URL / person / system / model |
| Explanation | value | deterministic reasoning output |
