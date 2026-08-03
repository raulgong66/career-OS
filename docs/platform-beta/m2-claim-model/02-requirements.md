# M2 Requirements — The Professional Claim Model

## Status

Proposal — architecture only. No implementation.

## Scope

Requirements define what the claim model must be able to express and support.
They do not define scoring, UI, storage, or code.

## 1. Claim Definition

**R1.1** A **Claim** is a first-class professional knowledge object: a discrete,
typed, human-readable statement about the professional that is asserted in one
or more recruiter-facing contexts.

**R1.2** A claim is **not** evidence. A claim is a statement; evidence is the
record that substantiates it. The model must keep the two kinds of object
distinct.

**R1.3** A claim may be supported by **zero to many** evidence items (ADR-002).
A claim with zero evidence is valid but weak, and must be flagged by the
Reasoning Engine (`strong_claim_without_evidence`).

**R1.4** Example claims the model must be able to represent:

- "I led the migration of mission-critical infrastructure to AWS."
- "I designed secure Kubernetes platforms."
- "I reduced deployment time by 60%."
- "I built AI-powered developer tooling."

## 2. Relationships

**R2.1** Evidence **supports** Claims (many-to-many). A single claim may
reference many evidence items; one evidence item may support multiple claims.

**R2.2** Claims are **used by** recruiter-facing artifacts. The supported set of
target contexts includes at minimum:

`professional_summary | experience | executive_profile | cv | linkedin |
biography | interview_answers | portfolio | presentation`

**R2.3** A claim may be used in **many** target contexts; a context draws from
**many** claims (many-to-many).

**R2.4** Claims may reference profile elements they depend on, via `skillRefs`
and `experienceRefs`, using the same `{ id, type }` reference shape as
ADR-002.

## 3. Claim Attributes

**R3.1** The model must express, at minimum, these attributes:

`id, title, statement, category, confidence, strength, targetContexts,
evidenceRefs, skillRefs, experienceRefs, tags, visibility, priority, status,
owner`

**R3.2** Attributes are model-level. Whether they are persisted as schema fields
or derived is an implementation decision, except where this document fixes them.

## 4. Claim Lifecycle

**R4.1** Claims move through states:

`draft → generated → reviewed → approved → deprecated → archived`

**R4.2** The model must define, for every transition, **who or what** may move a
claim (human professional, reviewer, LLM/extractor/import, reasoning engine,
administrator) — see `04-claim-lifecycle.md`.

## 5. Claim Strength

**R5.1** Strength is a **qualitative** level: `weak | supported | strong |
exceptional`.

**R5.2** No scoring algorithm is defined in this milestone. The model only
describes the **inputs** strength should eventually be derived from.

## 6. Explainability

**R6.1** The reasoning engine must be able to explain a claim along the path:

```
Claim → Evidence → Reasoning Rule → Recommendation
```

**R6.2** Every recommendation that touches document content must reference a
**Claim** (and its supporting Evidence), not a raw profile element.

## 7. Generation Pipeline

**R7.1** Document generation consumes claims, not raw elements, per:

```
Canonical Profile → Evidence → Claims → Target Context → Document
```

**R7.2** This pipeline **replaces** the current direct profile-to-document
generation in the Platform Beta vision. It is a target architecture, not a
migration requirement for Platform Alpha.

## 8. Schema

**R8.1** An illustrative YAML schema is provided in `05-schema-proposal.md`.
**R8.2** Worked examples across professions are provided in `06-examples.md`.
**R8.3** The claim schema is **illustrative only**; it does not modify
`schemas/profile.schema.json` and requires no migration.

## 9. Relationship to ADR-002

**R9.1** The claim model complements — never replaces — the evidence model:

- **Evidence** answers: *"How do we know?"*
- **Claim** answers: *"What are we saying?"*

**R9.2** Claims reference evidence using the ADR-002 reference contract
(`{ id, type }`, `verificationStatus` unchanged). Nothing in ADR-002 is
modified.

## 10. Open Questions

**R10.1** Unresolved architectural questions are catalogued in
`07-open-questions.md` and must not be silently decided in code.

## Non-Functional Requirements

**NFR-1** Model-only: no runtime scoring, no persisted computed strength.
**NFR-2** Storage-agnostic: the model must not assume a database.
**NFR-3** Deterministic: no randomness in identity, references, or selection.
**NFR-4** Extensible: new categories and target contexts must not require
schema reshaping.
**NFR-5** Privacy-safe: internal metadata (confidence, provenance, status) never
leaks into recruiter-facing output.
**NFR-6** Backward compatible with ADR-002: evidence and its reference shape are
untouched.
