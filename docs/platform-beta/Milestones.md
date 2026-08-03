# Platform Beta Milestones

These are **planning milestones only** - they define the sequencing of workstreams, not delivery commitments. Each milestone is scoped to a cohesive capability and decomposes into implementation tasks when work begins.

## Platform Beta M1 — Professional Evidence Model

- Introduce the first-class evidence entity and traceability from profile elements to backing evidence.
- Add structured achievements and measurable outcomes.
- Establish knowledge relationships between entities.
- Enable evidence-weighted optimization so recommendations are grounded in verified facts.

Workstream: A (Professional Knowledge) · feeds C, D

## Platform Beta M2 — Knowledge Acquisition Engine

- Continuous profile evolution with incremental imports.
- Conflict detection and profile merge.
- Human review workflow for every proposed profile change.

Workstream: B (Knowledge Acquisition) · feeds E

# Platform Beta Milestones (Revised)

These milestones reflect the current Platform Beta architecture and recent milestone completions. Platform Beta has evolved from a collection of generator-focused tasks into a workspace-oriented platform centered on the Canonical Profile, the Knowledge substrate (CSKS), and a set of user-visible Workspaces.

This document provides a concise milestone index. A complementary strategic roadmap and architectural justification are recorded in [docs/platform-beta/Roadmap-Vision.md](Roadmap-Vision.md).

## Completed milestones (high level)

- Platform Alpha (initial generator-focused product)
- Platform Beta Foundation (core architecture, canonical profile, schema, and reasoning foundations)
- M1.21 Artifact Workspace (Resume/Artifact workspace — frontend + transport + domain integration)
- M1.22 CSKS Foundation (CareerOS Self-Knowledge System — knowledge graph + explorer foundations)
- M1.22.1 CSKS Stabilization (stability and developer ergonomics)
- M1.23 CSKS Developer Experience (DX improvements: explorer, APIs, and integration points)

## Active roadmap — workspace-oriented milestones

The platform roadmap is organized into workspace-focused streams. Each stream groups coherent user-facing capabilities and their domain dependencies.

Workspaces and example milestones:

- Resume Workspace
	- M-R1: Artifact Workspace (M1.21) — completed
	- M-R2: Resume Recommendations & Scoring — proposed
	- M-R3: Resume History & Versioning — proposed

	Resume Workspace (concept)
	- Resume Health
	- Recommendations
	- Improvement Queue
	- Resume Generation (existing domain service)
	- Preview
	- History
	- Export

	Note: `Resume Generation` is an existing domain service (generation engine). The Resume Workspace orchestrates workflows, consumes the generation engine, and provides UX around health, preview, history and export.

- Tailoring Workspace
	- M-T1: Targeted Tailoring Flow (artifact tailoring + job description integration) — proposed
	- M-T2: Tailored Artifact Recommendation Engine — proposed

	Tailoring boundary
	- Resume Generation = improve and generate professional resumes from the Canonical Profile.
	- Tailoring = adapt artifacts for a specific Job Description.
	- Tailoring must consume existing `Resume Generation` services and must not duplicate generation logic. Tailoring is a consumer/orchestrator that provides JD normalization, mapping, and inputs into generation and scoring services.

- Interview Workspace
	- M-I1: Interview Simulation (M1.19) — completed
	- M-I2: Interview Feedback & Gap Analysis — proposed
	- M-I3: Recruiter Assistant (recruiter-facing Q&A) — proposed

- Knowledge Workspace (CSKS)
	- M-K1: CSKS Foundation (M1.22) — completed
	- M-K1.1: CSKS Stabilization (M1.22.1) — completed
	- M-K2: CSKS Explorer & Query UX (developer+user facing) — proposed
	- M-K3: Profile Quality Engine (automated checks and recommendations) — proposed

	Profile Quality Engine (future milestone)
	- Concept: a reusable, deterministic engine that evaluates `Canonical Profile` quality via deterministic quality rules and emits recommendations and resolution actions.
	- Conceptual flow:
		Canonical Profile
		↓
		Profile Quality Engine
		↓
		Deterministic Quality Rules
		↓
		Recommendations
		↓
		Resolution Workflow
		↓
		Updated Canonical Profile
	- Consumers: Resume Generation, Tailoring, Interview Intelligence, CSKS, Analytics
	- Note: `Resume Health` is a consumer view; the Profile Quality Engine is a reusable platform capability distinct from Resume Health.

- Platform Services
	- M-P1: Platform Analytics & Telemetry — proposed
	- M-P2: Event Bus / Workspace Framework — proposed
	- M-P3: Extension SDK / Plugin model — proposed

## Milestone overview (index)

| Milestone | Name | Stream | Status | Dependencies | Success criteria |
|---|---:|---|---|---|---|
| M1.21 | Artifact Workspace | Resume Workspace | Completed | Canonical Profile | Artifact workspace demo, end-to-end generation flow, API tests |
| M1.22 | CSKS Foundation | Knowledge Workspace | Completed | Canonical Profile | Schema, explorer prototype, data import examples |
| M1.22.1 | CSKS Stabilization | Knowledge Workspace | Completed | M1.22 | Stability fixes, developer ergonomics improvements |
| M1.23 | CSKS Developer Experience | Knowledge Workspace | Completed | M1.22.1 | DX improvements, example queries, dev docs |
| M-K2 | CSKS Explorer & Query UX | Knowledge Workspace | Proposed | M1.22.1 | Interactive explorer, query API, example queries |
| M-R2 | Resume Recommendations & Scoring | Resume Workspace | Proposed | M-K2, M1.21 | Scoring contract, example recommendations, API tests |
| M-T1 | Targeted Tailoring Flow | Tailoring Workspace | Proposed | M-R2, M1.21 | Tailoring flow, JD ingestion, generation inputs, end-to-end demo |
| M-I2 | Interview Feedback & Gap Analysis | Interview Workspace | Proposed | M-K2 | Feedback pipeline, gap analysis output, API tests |
| M-K3 | Profile Quality Engine | Knowledge Workspace | Proposed | M-K2 | Deterministic ruleset, recommendation outputs, resolution workflow |
| M-P2 | Event Bus / Workspace Framework | Platform Services | Proposed | M-R2, M-I2 | Event schemas, integration examples |

## Sequencing and dependencies (short)

- CSKS (M1.22) is foundational for analytics, recommendation, and workspace features. Many downstream milestones depend on CSKS capabilities.
- Artifact Workspace (M1.21) demonstrates the workspace pattern and should be used as the template for other workspace implementations.
- Interview Simulation remains a domain that consumes canonical profiles and CSKS; future Interview Workspace features depend on CSKS and the reasoning engine.

- CSKS (M1.22) is foundational for analytics, recommendation, and workspace features. Many downstream milestones depend on CSKS capabilities.
- Artifact Workspace (M1.21) demonstrates the workspace pattern and should be used as the template for other workspace implementations.
- Interview Simulation remains a domain that consumes canonical profiles and CSKS; future Interview Workspace features depend on CSKS and the reasoning engine.

Ordering note: prioritize `M-K2 (CSKS Explorer & Query UX)` before advanced Resume scoring/recommendation milestones (e.g., `M-R2`). Platform Services (events/SDK) should follow core workspace capabilities unless directly required.

For a detailed rationale, dependencies, and recommended next milestone see `docs/platform-beta/Roadmap-Vision.md`.
