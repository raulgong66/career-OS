# ADR 007: Interview Simulation & Session Lifecycle

## Status

Proposed

## Context

CareerOS Platform Beta has established the canonical profile, evidence model, claim model, Core boundaries, interview intelligence, and provider-agnostic AI abstractions. The next architecture milestone is Interview Simulation, which must consume Core services rather than introduce a parallel platform.

Interview Simulation is a new capability for rehearsing interview questions, capturing answer responses, evaluating session coverage, and generating feedback and reports. It must reuse existing platform objects and remain consistent with ADR-002 through ADR-006.

## Decision

1. Interview Simulation is implemented as a Core consumer module.
2. It reuses `InterviewPlan`, `EvidencePackage`, `ClaimSet`, `KnowledgeGraph`, `ReasoningEngine`, `RuleRegistry`, `ExportContract`, and the provider abstractions from ADR-006.
3. Session objects are external runtime artifacts, not part of the canonical profile.
4. Interview session state is persisted separately from the profile and stores only references to canonical evidence via ADR-002 `{id,type}`.
5. The session lifecycle is explicit: `Draft`, `Ready`, `In Progress`, `Paused`, `Completed`, `Reviewed`, and `Archived`.
6. Deterministic evaluation is authoritative. AI may enrich feedback but may never determine correctness.

## Knowledge Objects vs Runtime Objects

Interview Simulation distinguishes between durable professional knowledge and temporary execution state.

### Knowledge Objects

These are durable, canonical elements owned by `MANIFESTO.md` and the Canonical Professional Profile.

Examples:

- `Person`
- `Experience`
- `Skill`
- `Evidence`
- `Claim`
- `Achievement`
- `Certification`
- `Education`

Knowledge Objects belong to the Canonical Professional Profile and are the immutable source of professional truth.

### Runtime Objects

These are temporary execution objects used only during interview simulation.

Examples:

- `InterviewSession`
- `InterviewQuestionInstance`
- `InterviewAnswer`
- `SessionState`
- `EvaluationContext`
- `SessionMetrics`

Runtime Objects never become part of the Canonical Professional Profile. They reference Knowledge Objects through ADR-002 `{id,type}` evidence links, but they do not duplicate or own professional knowledge.

### Architectural consistency

This distinction is consistent with:

- `MANIFESTO.md`
- Knowledge Before Documents
- Knowledge Endures
- Single Source of Truth

It preserves the platform principle that professional knowledge is durable and owned by the canonical profile, while runtime activity is transient and session-scoped.

## Architecture

Interview Simulation is layered on top of Core:

- Core: canonical profile, evidence and claim models, knowledge graph, deterministic reasoning, export contract, generator registry, rule registry, provider abstractions.
- Interview Simulation module: session lifecycle, question instances, answer recording, evaluation results, feedback assembly, report generation.
- Future API: transport layer for sessions, answers, control actions, and reports.
- Frontend: user experience for interview rehearsal and review.

The dependency flow is strictly one-directional: Core → Interview Simulation → Future API → Frontend.

## Trade-offs

**Advantages**

- Preserves the canonical profile as the single source of truth.
- Prevents duplicated profile or evidence concepts inside session state.
- Keeps deterministic evaluation centralized in Core.
- Supports multiple independent sessions per profile.
- Enables review and archive without altering profile content.

**Disadvantages**

- The module requires a separate session persistence layer.
- Report generation reuses Core export pipelines, which may need adaptation for session-specific summaries.
- Session evaluation must be careful not to drift into profile mutation decisions.

## Alternatives considered

- Store interview sessions inside the canonical profile.
  - Rejected because it would blur the single source of truth and embed runtime session state in profile data.
- Treat sessions as generated artifacts inside the profile.
  - Rejected because session state is dynamic and not a persistent professional knowledge artifact.
- Implement a parallel session model outside Core.
  - Rejected because it would introduce duplicated reasoning and conflict with ADR-004.

## Future evolution

- The session persistence layer may evolve into a dedicated runtime store with session archives and review history.
- Evaluation rules may be extended through Core `RuleRegistry` and `ReasoningEngine` without changing the session model.
- AI enrichment may be formalized as advisory feedback generators behind the provider abstraction.
- The API may evolve to support session branching, multi-user review, and export formats.

## Relationship with ADR-002 through ADR-006

- ADR-002: Interview Simulation uses the evidence contract `{id,type}` for all canonical evidence references.
- ADR-003: Answer evaluation and report annotations reference canonical claims rather than ad hoc claim structures.
- ADR-004: Interview Simulation is a module that consumes Core and does not depend on other modules.
- ADR-005: Interview Simulation is a new Core consumer alongside Interview Intelligence.
- ADR-006: Interview Simulation uses provider abstractions for AI enrichment and does not tie to a specific provider.

## Relationship with the Manifesto

The decision aligns with the manifesto by keeping the canonical profile as the single source of truth, preserving deterministic reasoning, and using evidence as the basis for evaluation. Interview Simulation is an engineering extension of the platform, not a separate product line.
