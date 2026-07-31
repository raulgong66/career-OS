# M1 Problem Statement — The Professional Evidence Model

## Status

Proposal — architecture only. No implementation.

## Background

Platform Alpha shipped a canonical profile schema (`schemas/profile.schema.json`)
that includes a minimal `evidence` entity and `evidenceRefs` on experiences,
projects, skills, achievements, education, and certifications. In practice the
model is a stub:

- `evidence` items carry only `id`, `title`, `description`, `evidenceType`,
  `links`, and `relatedRefs`.
- There is no concept of provenance, verification, confidence, or lifecycle
  state.
- Real canonical profiles in the Alpha corpus contain **zero** evidence items,
  so the optimizer's `_get_backing_evidence` path (which walks `evidenceRefs`
  and `relatedRefs`) always returns nothing.

The Reasoning Layer (ADR 0005) and the Knowledge Graph were scoped but not
implemented. The document-generation pipeline therefore reasons over implicit
facts embedded in natural-language text rather than over explicit, verifiable
evidence.

## The Problem

Every Platform Beta capability described in `docs/platform-beta/Roadmap.md`
assumes a shared substrate:

| Workstream | Depends on evidence because… |
|---|---|
| A · Professional Knowledge | the profile must hold the *why* behind each claim, not just the claim |
| B · Knowledge Acquisition | imports must create evidence with provenance and merge without duplication |
| C · Reasoning Engine | findings and recommendations must be grounded and explainable |
| D · Professional Intelligence | analytics (skill evolution, trajectory, readiness) need measurable, dated evidence |
| E · Agentic AI | autonomous agents need a confidence model to decide when to ask for human review |
| F · Document Generation | recruiter-facing statements must be traceable back to supporting material |

Without a designed evidence model, each workstream would invent its own
ad-hoc notion of "proof." That is the exact failure mode this milestone exists
to prevent.

## Why Now

1. **Lowest-cost point of change.** No production code depends on evidence
   semantics beyond the stub. Designing now avoids a migration later.
2. **The foundation constraint.** Every entity added in later milestones
   (achievements, career claims, metrics, opportunity matches) will reference
   evidence. Getting the reference model wrong early propagates through all of
   them.
3. **Alpha compatibility.** The current `evidence` shape is a strict subset of
   what is proposed here. The model can be extended additively with zero
   breaking changes, and Platform Alpha behavior is preserved.

## Non-Goals (this milestone)

- No evidence *scoring* or confidence *computation* — only the model.
- No code, schema migration tooling, or tests.
- No changes to artifact generation, the optimizer, or any AI provider.
- No decision about which specific rules the Reasoning Layer will implement —
  only the contracts those rules will consume.

## Success Looks Like

A reviewer should be able to answer, for any recruiter-facing statement in a
generated document: **"What evidence supports this, how confident are we, and
where did that evidence come from?"**
