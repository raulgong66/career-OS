# M2 Problem Statement — The Professional Claim Model

## Status

Proposal — architecture only. No implementation.

## Background

ADR-002 established **Evidence** as the first-class source of truth in the
Professional Knowledge Platform. Evidence answers *"How do we know?"* — it
records verifiable artifacts (metrics, deployments, repositories, testimonials,
certifications) that substantiate facts about a professional.

ADR-0005 (Reasoning Layer) scoped a deterministic layer that produces Findings
and an Evidence Package consumed by AI providers. Today, however, the
generation pipeline still renders recruiter-facing documents **directly from
canonical profile elements** — experience paragraphs, skill lines — with no
intermediate semantic layer.

Recruiters do not evaluate raw profile elements. Recruiters evaluate
**claims**: "I led the migration of mission-critical infrastructure to AWS."
"I reduced deployment time by 60%." Evidence exists to support those claims.

## The Problem

Between Evidence (what we know) and Documents (what a recruiter reads) there is
no layer that expresses **"what are we saying?"**. The consequences:

1. **Duplication and drift.** The same statement is re-expressed independently
   in the CV, LinkedIn, biography, and interview answers. Editing one does not
   update the others, so the professional knowledge fragments.
2. **No tuning surface.** Nothing expresses "this claim is our strongest, use
   it prominently" versus "this claim is weak, demote or drop it." Every
   document re-derives emphasis from raw element text.
3. **No context targeting.** A CV and an interview answer highlight different
   aspects of the same history, but there is no model that selects and shapes
   claims per target context.
4. **Weak explainability.** ADR-0005 recommendations reference raw profile
   elements and graph nodes. There is no statement-level object a recommendation
   can point at, so "why did the CV lead with this?" has no precise answer.
5. **No reuse or evolution.** A claim refined once (e.g. sharper wording after
   review) cannot be reused everywhere the claim is cited.

## Why Now

M1 delivered the evidence foundation. Claims are the natural next layer: they
consume evidence (ADR-002) and they are consumed by the Reasoning Engine
(ADR-0005, workstream C) and Document Generation (workstream F). Designing the
claim model now prevents every workstream from inventing its own statement
abstraction.

## Non-Goals (this milestone)

- No implementation, no schema changes, no tests, no pipeline rewrite.
- No claim strength scoring algorithm — qualitative levels only.
- No migration of existing profiles to claims.
- No change to ADR-002, ADR-0005, or Platform Alpha behavior.

## Success Looks Like

Any recruiter-facing statement in any generated document can be traced to a
single first-class **Claim**, which is supported by **Evidence** and selected
for a **Target Context** — and every recommendation about that statement refers
to the Claim, not to a raw element.
