# M1 Requirements — The Professional Evidence Model

## Status

Proposal — architecture only. No implementation.

## Scope

Requirements define *what the evidence model must be able to express and
support*. They do not define scoring, UI, or code.

## 1. Evidence as a First-Class Entity

**R1.1** Evidence is a distinct, top-level entity with a stable identifier. It
is not an attribute of another element and not text embedded in a description.

**R1.2** The model must distinguish evidence **kinds** so that distinct types of
supporting material can be handled uniformly. Minimum kinds:

- `achievement`
- `project`
- `certification`
- `publication`
- `presentation`
- `customer_feedback`
- `recommendation`
- `metric`
- `kpi`
- `award`
- `github_repository`
- `production_deployment`
- `architecture_document`
- `oss_contribution`
- `document` (catch-all for importable files)

**R1.3** Evidence must be able to express **measurable outcomes** (metrics with
values, units, targets, and time periods) independently of narrative
description.

**R1.4** Evidence must carry **provenance**: where it came from (a file, a URL,
a person, a system, an import), and when it was captured.

**R1.5** Evidence must carry a **lifecycle state** so human review can gate its
use (e.g. draft, pending review, approved, rejected, archived).

## 2. Relationships

**R2.1** Evidence **supports** profile elements. The supported set includes at
minimum: Experience, Skill, Project, Certification, Education, Achievement,
Professional Summary, and Career Claim.

**R2.2** The relationship is **many-to-many**. Multiple evidence items may
support one element, and one evidence item may support multiple elements.

**R2.3** The reference is **bidirectionally consistent by design**: an element's
`evidenceRefs` and the evidence item's `relatedRefs` must agree. One side is the
source of truth; the other is derived or validated.

**R2.4** Evidence may exist without supporting any element (orphaned/uncategorized)
and must still be persisted and discoverable.

**R2.5** Elements must be referenceable with a stable identifier and a type tag
so evidence can point at any current or future element kind.

## 3. Confidence Model

**R3.1** The model defines a **verification status** for evidence, using exactly
these values:

- `verified` — independently confirmed (e.g. certificate registry, verifier,
  employer confirmation)
- `observed` — directly observed during capture (e.g. a live system,
  production deployment, witnessed outcome)
- `imported` — extracted from a source document such as a resume
- `generated` — produced by a machine (extractor, agent, reasoning engine)
- `user_confirmed` — the user reviewed and confirmed the evidence
- `estimated` — inferred with no direct source; should be flagged as such

**R3.2** The model defines the **inputs** to confidence (verification status,
provenance reliability, recency, completeness of measurement) but does **not**
define a scoring function. Scoring is deferred to a later milestone.

**R3.3** Verification status is recorded on the evidence item, not derived at
read time.

## 4. Traceability

**R4.1** Every recruiter-facing statement must be traceable, via a defined path,
to supporting evidence:

```
recruiter-facing statement
  → artifact content (sourceRef to a profile element)
  → profile element (evidenceRefs)
  → evidence item (provenance)
  → source (document / URL / person / system)
```

**R4.2** The trace path is a **read-only contract**. Generated artifacts carry
the *sourceRef* to the element; the element carries *evidenceRefs*; evidence
carries *provenance*. Nothing downstream mutates upstream.

**R4.3** Internal metadata (verification status, provenance, reasoning notes)
must never leak into recruiter-facing documents. Traceability is a knowledge
layer capability, not a rendering requirement.

## 5. Recommendation Engine Support

**R5.1** The model must allow the Reasoning Layer to detect and express at least
these conditions:

| Condition | Meaning |
|---|---|
| `strong_claim_without_evidence` | element with high asserted value and zero supporting evidence |
| `evidence_exists_but_unused` | evidence present that no generated artifact uses |
| `experience_unsupported` | experience whose claims are not substantiated by evidence |
| `duplicate_evidence` | two evidence items representing the same fact |
| `missing_measurable_outcomes` | a claim that is quantifiable but stated without numbers |

**R5.2** The model must expose the fields these conditions read: evidence count
per element, verification status per evidence, measured outcomes presence, and
evidence identity for deduplication.

## 6. Acquisition

**R6.1** Importing a resume must **create evidence** items (status `imported`,
provenance = the source document) and attach `evidenceRefs` to the profile
elements it creates.

**R6.2** Incremental imports must **merge** evidence rather than duplicate it:
matching is based on a canonical identity (see 03-domain-model), and the
result is one evidence item accumulating references from multiple imports.

**R6.3** When an incremental import conflicts with existing evidence, the model
must preserve both and mark the conflict for human review — never silently
overwrite.

## 7. Explainability

**R7.1** The reasoning engine must be able to produce, for any recommendation, an
explanation that references the specific evidence items (and their verification
status) that the recommendation rests on.

**R7.2** Explanations must be **deterministic**: the same graph and rules
produce the same explanation. No model output is required to explain a finding.

## 8. Schema

**R8.1** The proposed schema is documented as an illustrative YAML proposal
(`04-schema-proposal.md`) with a worked example (`05-example-profile.md`).

**R8.2** The future schema must be an **additive superset** of the current
`schemas/profile.schema.json` evidence definition. Anything that validates today
must validate after migration.

## 9. Migration

**R9.1** Migration is additive and backward compatible. No breaking changes to
existing profiles, artifact generation, optimizer, or AI providers.

**R9.2** Existing profiles with zero evidence remain valid and unchanged.

**R9.3** Evidence enrichment (populating evidence for legacy profiles) is an
optional, separate effort — not a migration requirement.

## Non-Functional Requirements

**NFR-1** Model-only: no runtime scoring, no persisted computed confidence.
**NFR-2** Storage-agnostic: the model must not assume a database.
**NFR-3** Deterministic: no randomness in identity or relationship definitions.
**NFR-4** Extensible: new evidence kinds and new supported element types must not
require schema reshaping.
**NFR-5** Privacy-safe: recruiter-facing output never contains internal metadata.
