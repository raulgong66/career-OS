# Interview Simulation Implementation Guidelines

This document defines the engineering guidance for future Interview Simulation implementation work. It is an architecture reference, not an implementation plan.

## Architectural invariants

- The Canonical Professional Profile is the single source of truth.
- Interview Simulation is a module that consumes Core services, not a source of knowledge.
- Knowledge Objects belong to the profile; Runtime Objects belong to session execution.
- Session state may reference canonical knowledge through ADR-002 `{id,type}` evidence links, but it does not contain canonical knowledge.
- Deterministic evaluation is authoritative. AI may enrich language and advice, but it does not determine correctness.
- Module dependencies must follow Core → Interview Simulation → API → Frontend.

## Dependency rules

- Interview Simulation may depend only on Core and shared platform abstractions.
- It must not depend on other modules such as AI Tailoring, Recruiter Assistant, or application-specific services.
- It must not import provider-specific AI SDKs or vendor code directly.
- It may consume provider abstractions defined in ADR-006 for enrichment.
- It may consume `InterviewPlan`, `KnowledgeGraph`, `ReasoningEngine`, `RuleRegistry`, `ExportContract`, and evidence/claim contracts from Core.

## Serialization conventions

- Persisted objects must serialize explicit evidence references as `{id,type}` according to ADR-002.
- Do not serialize internal reasoning metadata as part of session state or exported reports.
- Separate persisted session fields from transient runtime fields.
- Exported session objects should include only canonical references and evaluation summaries, not raw knowledge fragments.
- Use clear `to_dict()` / `to_json()` methods for interoperability.

## Immutable model guidelines

- Treat domain model objects as immutable records where possible.
- Runtime session state may change, but it should never mutate canonical knowledge objects.
- Use immutable snapshots for `InterviewPlan`, `InterviewQuestion`, and evidence citations.
- Avoid mutable shared objects across sessions.

## Naming conventions

- Knowledge-owned objects should use profile-relevant names: `Person`, `Experience`, `Evidence`, `Claim`, `Achievement`, `Certification`, `Education`.
- Runtime/session objects should use execution-oriented names: `InterviewSession`, `InterviewQuestionInstance`, `InterviewAnswer`, `SessionState`, `EvaluationContext`, `SessionMetrics`, `FeedbackItem`, `ReportSection`.
- Use `*Ref` or `*Reference` for evidence/claim links to canonical profile elements.
- Reserve `*Plan` for immutable session templates such as `InterviewPlan`.

## Testing expectations

Implementers should verify:

- Evidence references are always persisted as ADR-002 `{id,type}`.
- InterviewSimulation logic does not create or mutate canonical profile data.
- Deterministic plan generation produces repeatable results from the same profile.
- Provider-agnostic abstractions are used for AI enrichment.
- Session state transitions follow the documented lifecycle.
- Exported reports do not leak internal metadata or profiling artifacts.

## Common implementation mistakes to avoid

- Storing profile fragments or narrative prose inside session state.
- Treating runtime objects as knowledge objects.
- Importing AI provider SDKs directly into the module.
- Duplicating reasoning logic already owned by Core.
- Using numeric scores when the claim model expects qualitative evaluation.
- Persisiting transient prompt state or local UI state in session archives.

## Review checklist for future milestones

- Does the implementation preserve the Canonical Professional Profile as the single source of truth?
- Are runtime objects separated from knowledge objects?
- Are all canonical references stored as ADR-002 evidence links?
- Is evaluation deterministic and rule-driven, with AI only enriching output?
- Does this module depend only on Core and provider abstractions, not on other modules?
- Are persisted session objects free of internal reasoning metadata?
- Are naming conventions consistent and semantically clear?
- Is the session lifecycle implemented as a state machine separate from profile state?
- Does exported report content remain evidence-backed and traceable?
