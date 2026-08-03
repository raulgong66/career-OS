# ADR 005: Interview Intelligence Module

## Status

Proposed

## Context

CareerOS is a Professional Knowledge Platform whose Core (`careeros/`) owns the canonical profile, knowledge graph, reasoning engine, evidence model (ADR-002), claim model (ADR-003), resolution engine, export contract, and artifact lifecycle. AI Tailoring is the first module built on that Core.

The next module is **Interview Intelligence**: candidate preparation, interview simulation, and a recruiter assistant whose answers must be grounded in the canonical profile. Without a designed module, Interview Intelligence risks:

- **Duplicate reasoning.** Re-analyzing the profile for weaknesses, measurability, or concepts instead of reusing `ReasoningEngine`/`RuleRegistry` and the concept taxonomy.
- **Duplicate knowledge.** A second notion of evidence, claims, or skills beside ADR-002/ADR-003.
- **Profile mutation.** Writing canonical profile data directly instead of through Core services and the review workflow.
- **Grounding failures.** A recruiter assistant that answers without citations, or leaks internal metadata (violating the ADR-002 traceability and metadata-privacy guarantees).

ADR-004 established the Core / Module / App boundary. Interview Intelligence is the first module designed under it, so its shape becomes the pattern for future modules (Career Analytics, Learning Planner, Application Tracking, Skill Gap Analysis).

## Decision

Adopt **Interview Intelligence as a Core consumer module** with the following commitments:

1. **Module boundary.** It lives as a module package (e.g. `careeros/interview/`) composed into the apps (`api/`, `frontend/`). It imports Core only — never AI Tailoring internals, and never the tailoring UI/API.
2. **Three capabilities.** Candidate Preparation, Interview Simulation, and Recruiter Assistant, sharing one domain model.
3. **No duplicate knowledge.** Module objects reference canonical elements via the ADR-002 reference contract (`{id, type}` / `evidenceRefs`). Facts, evidence, and claims remain Core-owned.
4. **No duplicate reasoning.** Analysis is contributed by new `Rule`s registered into the Core `RuleRegistry`. The module consumes `ReasoningFindings` for weak areas, strengths, and missing competencies; reuses the measurability heuristic and the concept/requirement taxonomy through their public APIs.
5. **Grounded recruiter answers.** Every `RecruiterAnswer` carries citations to canonical elements/evidence. No fabricated facts; if data is absent, the answer states the gap. Internal reasoning metadata never crosses into recruiter output.
6. **Qualitative evaluation.** Feedback and evaluation use qualitative levels (`weak | supported | strong | exceptional`) consistent with ADR-003. No numeric scores are stored or exposed.
7. **Profile integrity.** The module never writes the canonical profile. Prep/report suggestions that imply profile changes flow through the existing review workflow (`review_callback` / `ProfileState`). Session/plan/report state is module-local.
8. **Document reuse.** Preparation guides and interview reports are artifacts: built via `ExportContractBuilder`, rendered by the Core generation pipeline using registered templates, and governed by the artifact lifecycle (current/stale, explicit regeneration).

## Architecture

```
CareerOS Platform
├── Core (careeros/)  ← unchanged; no dependency on any module
└── Modules
    ├── AI Tailoring (existing)
    └── Interview Intelligence (new)
        ├── domain         — models, enums, reference contracts
        ├── preparation    — question generation, suggested answers, guides
        ├── simulation     — sessions, evaluation, feedback, reports
        ├── recruiter      — intent classification, query plans, grounded answers
        ├── rules          — RuleRegistry extensions (Core-hosted analysis)
        └── api            — (future) thin route handlers
```

Dependency direction is strictly one-way: `Core ← Modules ← Apps`. Detailed diagrams in `04-architecture.md`.

## Responsibilities

| Layer | Responsibilities |
|---|---|
| Core | Canonical profile, schema/validation, knowledge graph, reasoning + rule registry, evidence/claims, resolution, export contract, generation, artifact lifecycle, review workflow |
| Interview Intelligence | Question/template instantiation, session state machine, deterministic answer evaluation + feedback, suggested-answer outlines, recruiter query planning, guide/report documents |
| Apps | Transport, DTOs, error mapping, UI, module composition |

The module is responsible for *interpretation and interaction* (asking, answering, evaluating); Core remains responsible for *facts and analysis*.

## Core Dependencies

Reused, never duplicated (full mapping in `03-core-integration.md`):

- **Canonical Profile + `ProfileRepository`/`ProfileLoader`** — grounding for all questions, answers, and recruiter responses.
- **Schema + `EntityValidator`** — validate persisted module entities and profile reads.
- **`KnowledgeGraph`** — navigation (skills→experiences→projects→achievements→evidence) for targeting and recruiter lookups.
- **`ReasoningEngine` + `RuleRegistry`** — weak areas, strengths, missing competencies; host for new interview rules.
- **Evidence model (ADR-002)** — `EvidenceCitation` grounding; recruiter evidence queries.
- **Claim model (ADR-003)** — suggested answers; `interview_answers` target context.
- **Achievements** — STAR answers and measurable-outcome evaluation.
- **Measurability heuristic** — answer outcome check (public API to be exposed before implementation).
- **Concept/requirement taxonomy** — role keywords and project-theme matching (e.g. "AWS migration").
- **`ExportContractBuilder` + `TemplateRegistry` + generation pipeline** — prep guides and reports.
- **Artifact lifecycle** — persist/regenerate guide and report artifacts.
- **Review workflow** — the only path for profile changes implied by interview feedback.

## Future Evolution

- **M1.13 (recommended):** public `is_measurable` helper in `careeros/resolution.py`; skeleton module package with domain models only; a small set of deterministic question templates and a recruiter evidence-lookup query plan against a sample profile.
- **Claim-mediated answers:** when ADR-003's claim layer is implemented, suggested answers migrate to claim selection for the `interview_answers` context; until then they source from achievements/evidence with claim-shaped outlines.
- **New interview rules:** register rules (e.g. `AnswerMissingEvidence`, `AnswerMissingMetric`, `AnswerMissingStarResult`) into the Core `RuleRegistry` — visible to every future module, not just interview.
- **Recruiter assistant hardening:** deterministic intent classification → optional LLM rephrasing of cited facts only; profile-gap answers feed recommendations through the existing flow.
- **Cross-module reuse:** the pattern here (module → Core only, rules as the analysis seam, artifacts as the document seam) is the template for Career Analytics, Learning Planner, Application Tracking, and Skill Gap Analysis.

## Consequences

**Positive:** grounding guarantees; no duplicate reasoning/knowledge; clean seam for future modules; evaluative feedback consistent with ADR-003; recruiter outputs honor metadata privacy.

**Negative:** requires exposing a few public Core helpers before implementation; module state persistence (sessions/reports) is new; claim-mediated answers wait on ADR-003 implementation.
