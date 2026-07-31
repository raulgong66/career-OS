# ADR 003: Professional Claim Model

## Status

Proposed

## Context

ADR-002 established **Evidence** as the first-class source of truth: verifiable
records (metrics, deployments, repositories, testimonials, certifications) that
answer *"How do we know?"*. ADR-0005 scoped a deterministic Reasoning Layer that
produces Findings and an Evidence Package consumed by AI providers.

However, the architecture has a missing semantic layer between Evidence and the
recruiter-facing artifacts. Generation still renders documents directly from
raw canonical profile elements (experience paragraphs, skill lines). Recruiters
do not evaluate raw elements — they evaluate **claims**: discrete, typed
statements such as "I led the migration of mission-critical infrastructure to
AWS" or "I reduced deployment time by 60%."

Without a claim layer, the Platform Beta vision degrades in five concrete ways:

- **Duplication and drift.** The same statement is re-expressed independently
  in the CV, LinkedIn, biography, and interview answers; editing one does not
  update the others, fragmenting professional knowledge.
- **No tuning surface.** Nothing expresses "this claim is strong, feature it"
  versus "this claim is weak, demote it."
- **No context targeting.** A CV and an interview answer should highlight
  different claims, but no model selects or shapes claims per target context.
- **Weak explainability.** ADR-0005 recommendations reference raw elements and
  graph nodes; they cannot point at the *statement* being made.
- **No reuse or evolution.** A claim refined once cannot be reused everywhere
  it is cited.

## Decision

Adopt a **first-class Professional Claim Model** as the semantic layer between
Evidence (ADR-002) and recruiter-facing documents, defined in
`docs/platform-beta/m2-claim-model/`, with these commitments:

1. **A Claim is a first-class professional knowledge object.** It carries
   identity, category, a human-readable `statement`, confidence inputs, a
   qualitative strength level, evidence references, anchoring references,
   target contexts, visibility, priority, status, owner, and an append-only
   history. A claim is **not** evidence; a claim is **supported by** evidence.

2. **Relationships are many-to-many and layered.** Evidence `supports` claims
   (one evidence item may support many claims; one claim may reference many
   evidence items). Claims are `used by` target contexts (`professional_summary
   | experience | executive_profile | cv | linkedin | biography |
   interview_answers | portfolio | presentation`) using the ADR-002 reference
   contract. Claims anchor to profile elements via `skillRefs`/`experienceRefs`.

3. **Strength is qualitative, not scored.** `weak | supported | strong |
   exceptional` are levels, not numbers. The model fixes the *inputs* strength
   will eventually be derived from (evidence volume, verification-status mix,
   measurable outcomes, recency, review approval, cross-context reuse); scoring
   is deferred to the Professional Intelligence milestone.

4. **Confidence is inputs only.** A claim's confidence aggregates the ADR-002
   verification statuses of its supporting evidence and its own review state.
   No score is stored or computed in this model.

5. **Lifecycle is governed.** `draft → generated → reviewed → approved →
   deprecated → archived`, with explicit actors for every transition
   (professional, reviewer, LLM/extractor/import, reasoning engine,
   administrator). `generated` claims never enter documents without review;
   deprecation from evidence withdrawal is flag-then-confirm.

6. **Recommendations reference claims, not raw elements.** Every recommendation
   that touches document content points at a Claim and its Evidence along the
   deterministic path `Claim → Evidence → Reasoning Rule → Recommendation`.

7. **The generation pipeline is claim-mediated.** Target architecture:
   `Canonical Profile → Evidence → Claims → Target Context → Document`. This
   **replaces** direct profile-to-document generation in the Platform Beta
   vision; it is a target, not a Platform Alpha migration.

8. **Claims complement, never replace, evidence.** Evidence answers "How do we
   know?"; claims answer "What are we saying?". ADR-002 is unmodified.

This milestone produces design documents only: `01-problem-statement.md`,
`02-requirements.md`, `03-domain-model.md`, `04-claim-lifecycle.md`,
`05-schema-proposal.md`, `06-examples.md`, `07-open-questions.md`, and this ADR.

## Alternatives Considered

1. **No claim layer; generate directly from profile elements (status quo).**
   Rejected. Perpetuates duplication, drift, weak explainability, and gives no
   tuning or context-targeting surface — the exact problems this ADR exists to
   solve.
2. **Claims as derived views of evidence, not persisted objects.** Rejected. A
   non-persisted statement cannot carry governance (review, approval,
   deprecation), ownership, or stability across documents. The lifecycle
   requires a durable object.
3. **Claim strength as a computed score in this milestone.** Rejected. Scoring
   before the Reasoning Engine exists would freeze semantics and create false
   precision. Qualitative levels plus derivation inputs are sufficient now.
4. **Claims inlined into the canonical profile schema.** Deferred. The claim
   layer is a distinct knowledge layer with its own lifecycle; merging it into
   the profile schema would couple authoring governance to the canonical record
   and force a breaking schema change. It is modeled separately, though it
   references profile elements.
5. **One claim per target context (no sharing).** Rejected. Violates the reuse
   requirement (R2.2); contexts reference claims rather than copying text, so a
   single claim legitimately serves many contexts.

## Consequences

**Positive:**

- One statement is authored, governed, and reused across all recruiter-facing
  contexts — eliminating duplication and drift.
- Recommendations and explanations gain a precise, statement-level target
  (stronger ADR-0005 explainability).
- Context targeting and claim strength become expressible before scoring.
- The pipeline's target shape is documented before workstreams C and F build on
  it, avoiding per-workstream statement abstractions.
- Fully backward compatible: ADR-002 evidence and its reference contract are
  untouched; Platform Alpha generation is unchanged.

**Negative:**

- Adds a new layer to design and maintain before any runtime value appears.
- Claim selection/ordering semantics remain open (Q6, Q7) and will need
  Reasoning-Engine decisions.
- Risk of claim-element duplication (Q12) until workstream F defines the
  source-of-truth boundary.
- Documentation and validation surface grows alongside ADR-002's.

## Future Extensions

- **Strength scoring mapping** (M3): deterministic mapping from the derivation
  inputs onto `weak | supported | strong | exceptional`.
- **Claim identity and deduplication** (M4): canonical identity for claims,
  analogous to ADR-002 evidence identity (Q11).
- **Context variants and localization** (workstream F): per-context or
  per-locale renderings of one claim (Q6, Q10).
- **Recruiter feedback channel** (M3/M4): feedback as a claim-level or
  evidence-level signal requiring human review (Q8).
- **Recency/freshness semantics** (M3): expiry windows distinct from confidence
  (Q4, Q5).
- **Versioned claim edits** (M4): edit-after-approval with version history
  (Q1).
- **Claim-mediated generation** (workstream F): the documented pipeline becomes
  the implemented one, replacing direct profile-to-document generation.
