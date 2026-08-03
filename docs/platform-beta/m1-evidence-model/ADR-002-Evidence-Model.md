# ADR 002: Professional Evidence Model

## Status

Proposed

## Context

Platform Alpha shipped a canonical profile schema (`schemas/profile.schema.json`)
containing a minimal `evidence` entity — `id`, `title`, `description`,
`evidenceType`, `links`, `relatedRefs`, `extensions` — and `evidenceRefs` on
experiences, projects, skills, achievements, education, and certifications. In
practice the model is unpopulated: canonical profiles carry no evidence items,
so reasoning about *why* a claim is true is impossible.

Every Platform Beta workstream in `docs/platform-beta/Roadmap.md`
(Professional Knowledge, Knowledge Acquisition, Reasoning Engine, Professional
Intelligence, Agentic AI, Document Generation) assumes a shared substrate that
can express: what a fact is, how confident we are in it, where it came from,
and what it supports. Without a designed evidence model, each workstream would
define its own ad-hoc notion of proof, producing incompatible, unmergeable
concepts.

The Reasoning Layer (ADR 0005) requires deterministic, evidence-grounded
findings, and traceability (recruiter-facing statements back to supporting
material) is a stated Beta principle in `docs/platform-beta/README.md`. No
existing design provides these primitives.

## Decision

Adopt a **first-class Professional Evidence Model** as the foundation of
Platform Beta, defined in `docs/platform-beta/m1-evidence-model/`, with these
commitments:

1. **Evidence is a top-level entity.** It carries identity, kind, provenance,
   confidence inputs, measurable outcomes, lifecycle state, and references to
   the elements it supports.
2. **Relationships are many-to-many.** Evidence supports multiple elements
   (Experience, Skill, Project, Certification, Education, Achievement,
   Professional Summary, Career Claim) and elements reference multiple evidence
   items. Element → evidence (`evidenceRefs`) is authoritative;
   evidence → elements (`relatedRefs`) is the derived reverse index.
3. **Confidence is model-only, not scoring.** The model stores the *inputs* to
   confidence — `verificationStatus` (`verified | observed | imported |
   generated | user_confirmed | estimated`), provenance source kind, recency,
   completeness, and `reviewState`. No scoring function is defined now; scoring
   is deferred to the Professional Intelligence milestone.
4. **Traceability is a read-only contract.** Recruiter-facing statement →
   element (`sourceRef`) → evidence (`evidenceRefs`) → provenance (source,
   capturedAt). Internal metadata never crosses into recruiter-facing output.
5. **The schema extension is additive and backward compatible.** The future
   schema is a strict superset of the current `evidence` definition. New fields
   are optional with defaults; `description`→`summary` and
   `evidenceType`→`kind` are aliased during transition. Nothing that validates
   today is invalidated.
6. **Acquisition merges, never duplicates.** Imports create evidence with
   status `imported` and provenance; incremental imports match on canonical
   identity and merge references. Conflicts are preserved and flagged for human
   review, never silently overwritten.
7. **Reasoning and explainability are deterministic.** The model must expose
   the inputs for conditions such as `strong_claim_without_evidence`,
   `evidence_exists_but_unused`, `experience_unsupported`,
   `duplicate_evidence`, and `missing_measurable_outcomes`, and every finding
   must be explainable by referencing specific evidence and its status.

This milestone produces design documents only: `01-problem-statement.md`,
`02-requirements.md`, `03-domain-model.md`, `04-schema-proposal.md`,
`05-example-profile.md`, `06-migration-strategy.md`, `07-open-questions.md`, and
this ADR.

## Alternatives Considered

1. **Keep the minimal stub, extend per-workstream.** Rejected. Would create
   incompatible notions of proof across Beta workstreams and force a costly
   unification later. The whole point of the foundation is to avoid this.
2. **No explicit evidence entity; rely on narrative text.** Rejected. Narrative
   cannot be referenced, verified, merged, or reasoned over deterministically.
   Contradicts ADR 0005 and the traceability principle.
3. **Evidence stored in a separate external store (DB/object store) from day
   one.** Deferred. The model is storage-agnostic by design; introducing
   storage is a later implementation decision and not needed for the schema
   contract.
4. **Confidence as a stored numeric score.** Rejected for now. Scores without a
   defined derivation create false precision, freeze the model before the
   scoring layer exists, and complicate migration. The model stores inputs
   instead.
5. **Unidirectional refs only (elements → evidence).** Considered but extended:
   the reverse index (`relatedRefs`) is kept as a *derived* index for the
   `evidence_exists_but_unused` signal and graph navigation, with element →
   evidence as the authority.

## Consequences

**Positive:**

- Every Beta workstream builds on one consistent, documented model.
- Traceability and explainability (Beta principles) have concrete primitives.
- Additive extension keeps Platform Alpha fully intact; no breaking changes.
- Deterministic reasoning (ADR 0005) gains a stable substrate.
- Import merging and deduplication have a defined identity contract.

**Negative:**

- Upfront design cost with no runtime value until a Beta workstream consumes it.
- The proposal may need revision when M2/M3 owners resolve the open questions
  in `07-open-questions.md`.
- Adds documentation and validation surface that must be maintained.

## Future Extensions

- **Confidence scoring layer** (M3/D): deterministic function over the stored
  inputs; the model already defines the inputs.
- **Canonical identity + fingerprinting** (M2): resolves Q1–Q3 and powers merge.
- **Unit/metric normalization and aggregation** (M3): resolves Q9–Q10.
- **Verification chain auditability** (M2): full provenance history including
  re-verification events (Q12).
- **Link visibility marking** (F/security): prevents internal URLs from leaking
  into recruiter-facing output (Q13).
- **Rule registry mapping** (M3): official mapping from evidence model fields to
  Reasoning Layer conditions.
- **Cross-profile evidence sharing** (platform core, out of current scope): Q14.
- **Evidence kind extensibility** (ongoing): open enums allow new kinds without
  schema reshaping (R2.5, NFR-4).
