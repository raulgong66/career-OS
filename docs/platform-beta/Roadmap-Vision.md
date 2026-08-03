# Platform Beta Roadmap & Vision

## Executive summary

Platform Beta transitions CareerOS from a generator-centric product to a workspace-oriented platform that centers the Canonical Profile and the CareerOS Self-Knowledge System (CSKS). Workspaces are the primary user-facing units (Resume, Tailoring, Interview, Knowledge) while platform services and developer experience enable scale, integrations, and extensibility.

This document explains the vision, rationale, dependencies, risks, and recommended next milestones.

## Product vision

- Canonical Profile as the single source of truth (ADR-003): every workspace consumes and enriches this canonical representation.
- CSKS (CareerOS Self-Knowledge System): a knowledge substrate that powers analytics, recommendations, and evidence-tracing for all workspaces.
- Workspaces: focused, discoverable UI/UX flows that surface capabilities for specific user jobs-to-be-done while reusing shared domain services and the canonical profile.
- Transport-only API: the API layer must remain a thin transport that delegates logic to domain engines in `careeros/`.

## Architectural guardrails

- Frontend: presentation only; orchestrates flows and calls API endpoints.
- API: transport layer; map DTOs and forward to domain services.
- Domain: owns business logic, validation, and side effects (persistence, evaluation, artifact generation).
- Canonical Profile: immutable canonical schema and transformation contracts; any derivations must be reversible or traceable.

## Roadmap structure

- Organize milestones by Workspaces (Resume, Tailoring, Interview, Knowledge) plus Platform Services (analytics, events, SDKs).
- Each workspace milestone should provide: UX, transport endpoints, domain integration, tests, and a small demo flow.
- Prioritize milestones that unlock multiple downstream features (CSKS, Artifact Workspace pattern).

- Organize milestones by Workspaces (Resume, Tailoring, Interview, Knowledge) plus Platform Services.
- Each workspace milestone should provide: UX, transport endpoints, domain integration, tests, and a small demo flow.
- Prioritize milestones that unlock multiple downstream features (CSKS, Artifact Workspace pattern) and specifically prioritize CSKS Explorer before advanced scoring.

Resume Generation and Resume Workspace

- `Resume Generation` is an existing domain service (generation engine) that produces artifacts from the Canonical Profile. Do not replace or redesign it here.
- A `Resume Workspace` is an orchestration layer and UX that consumes the existing `Resume Generation` service and provides:
   - Resume Health
   - Recommendations
   - Improvement Queue
   - Resume Generation (existing)
   - Preview
   - History
   - Export

Tailoring boundary and integration

- `Resume Generation` = improve and generate professional resumes from the Canonical Profile.
- `Tailoring` = adapt artifacts for a specific Job Description.
- Tailoring MUST consume existing `Resume Generation` services and MUST NOT duplicate generation logic. Tailoring supplies JD normalization and mapping as inputs to generation and scoring.

Profile Quality Engine (concept)

- Introduce a reusable, deterministic `Profile Quality Engine` as a future platform capability. This is distinct from `Resume Health` (a consumer view).
- Conceptual flow:
   - Canonical Profile → Profile Quality Engine → Deterministic Quality Rules → Recommendations → Resolution Workflow → Updated Canonical Profile
- Consumers: Resume Generation, Tailoring, Interview Intelligence, CSKS, Analytics
- The Profile Quality Engine should be positioned as a knowledge/platform capability that emits deterministic, traceable recommendations rather than ad-hoc heuristics.

## Recent progress (context)

- Artifact Workspace (M1.21): frontend artifact workspace + transport + domain integration implemented and validated in tests.
- Interview Simulation (M1.19): domain, engine, API endpoints, and frontend practice page implemented and unit-tested.
- CSKS Foundation (M1.22 series): schema, explorer foundations, and stability patches completed.
- Project Operations Manual created to unify developer and contributor workflows.

## Strategic priorities and rationale

1. Stabilize CSKS and APIs
   - Why: CSKS is the knowledge foundation; stability reduces friction for downstream workspace teams.
   - Actions: harden schema, add migration tests, improve DX, create example queries and benchmarks.

2. Expand the Workspace pattern
   - Why: Workspaces reduce surface area for UX and encourage reuse of domain services.
   - Actions: replicate Artifact Workspace scaffold for Interview and Tailoring; create workspace starter templates.

3. Recommendation & Scoring Engines
   - Why: Tailoring and Resume improvements depend on robust scoring and explainability.
   - Actions: define scoring contracts, add evidence-weighted heuristics, expose evaluation endpoints.

4. Platform Services (Event Bus + SDK)
   - Why: Need scalable integration for telemetry, extensions, and cross-workspace coordination.
   - Actions: prototype event bus, define extension SDK, document integration patterns.

## Risks

- Premature coupling: implementing workspace UX directly against domain internals may entangle API contracts. Mitigation: enforce DTO boundaries and API-only integration tests.
- Schema instability: frequent breaking changes to the canonical profile will ripple across workspaces. Mitigation: semver, migration scripts, compatibility tests.
- Scope creep: workspaces risk becoming full-featured product areas. Mitigation: define minimal shippable flows per milestone and use MVE (minimum valuable experience) gate.

## Recommended immediate next milestone

- M-K2: CSKS Explorer & Query UX
  - Why: Unlocks discovery, developer adoption, and powers scoring and reasoning engines.
  - Scope: interactive explorer, query API, example queries, basic pagination, and security rules.
  - Success criteria: explorer UI (local dev), API tests, example query library, performance baseline.

## Milestone sequencing (suggested)

1. M-K2 (CSKS Explorer & Query UX)
2. M-R2 (Resume Recommendations & Scoring)
3. M-I2 (Interview Feedback & Gap Analysis)
4. M-T1 (Targeted Tailoring Flow)
5. M-P2 (Event Bus / Workspace Framework)

## Next steps for the team

- Approve milestone priorities and owners for M-K2 and M-R2.
- Create milestone-level issue tracking (GitHub milestones + lightweight specs).
- Add integration tests that validate API-only interactions for one workspace (use Artifact Workspace as template).

## Appendix: artifact templates and workspace template

- Use `frontend/src/pages/ArtifactWorkspacePage.tsx` and `frontend/src/services/ArtifactService.ts` as the Artifact Workspace scaffold.
- Use `api/interview_dto.py` and `careeros/interview` domain implementations as an Interview Workspace reference.


-- End of document
