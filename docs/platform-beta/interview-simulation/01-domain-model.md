# Interview Simulation Domain Model

This document defines the domain model for Interview Simulation as a Core consumer within CareerOS Platform Beta.

Interview Simulation reuses existing Core concepts and does not introduce a parallel professional knowledge model. All new session objects reference canonical entities through the ADR-002 evidence contract (`{id,type}`) rather than duplicating profile data.

## Knowledge Objects vs Runtime Objects

Interview Simulation distinguishes between durable professional knowledge and temporary execution state.

### Knowledge Objects

Knowledge Objects represent durable professional information stored in the Canonical Professional Profile.

Examples:

- `Person`
- `Experience`
- `Skill`
- `Evidence`
- `Claim`
- `Achievement`
- `Certification`
- `Education`

These objects belong to the Canonical Professional Profile and are governed by the platform’s evidence and claim contracts.

### Runtime Objects

Runtime Objects represent temporary session execution state and never become part of the Canonical Professional Profile.

Examples:

- `InterviewSession`
- `InterviewQuestionInstance`
- `InterviewAnswer`
- `SessionState`
- `EvaluationContext`
- `SessionMetrics`

Runtime Objects reference Knowledge Objects through ADR-002 `{id,type}` evidence links, but they do not duplicate or own professional knowledge.

### Architectural consistency

This distinction supports the platform principles:

- `MANIFESTO.md`
- Knowledge Before Documents
- Knowledge Endures
- Single Source of Truth

It ensures that Interview Simulation remains a consumer of professional knowledge rather than an alternate source.

## Core objects

The following objects are defined in Core and reused by Interview Simulation:

- `CanonicalProfessionalProfile`
  - The single source of truth for all professional knowledge.
- `InterviewPlan`
  - The existing interview plan object that defines questions, goals, target contexts, and evidence expectations.
- `InterviewQuestion`
  - A question definition owned by the interview plan and validated against the profile.
- `EvidencePackage` / `EvidenceItem`
  - Canonical evidence references. Interview Simulation stores evidence pointers as `{id,type}` according to ADR-002.
- `ClaimSet`
  - Canonical claim references used for answer evaluation and report generation.
- `TargetContext`
  - Reusable context definitions for InterviewPlan, prompt templates, and evaluation rules.

## Module-owned objects

The Interview Simulation module owns runtime session objects and evaluation results:

- `InterviewSession`
  - The core session object that tracks session metadata, status, question instances, answers, metrics, and derived artifacts.
  - References the `InterviewPlan` and the profile through evidence IDs, but does not duplicate canonical profile content.
- `InterviewQuestionInstance`
  - A module-specific question occurrence within a session.
  - Includes question state, sequencing metadata, and references to relevant evidence IDs.
- `InterviewAnswer`
  - A session answer object containing the respondent text, selected evidence references, confidence metadata, and any attachments.
  - References canonical evidence through ADR-002-style `{id,type}` links.
- `AnswerEvaluation`
  - A deterministic evaluation result for an answer.
  - Includes pass/fail indicators, coverage metrics, structure checks, and consistency observations.
- `InterviewFeedback`
  - A curated set of advisory guidance items produced by evaluation and AI enrichment.
  - Contains references to evidence items, question coverage, and required follow-up actions.
- `InterviewReport`
  - A generated session artifact summarizing performance, strengths, gaps, and next steps.
  - Derived from session state and canonical profile evidence.
- `InterviewSummary`
  - A concise version of the report for review and planning.
- `SessionMetrics`
  - Numeric and qualitative metrics for a session, such as coverage, confidence, evidence density, and question completion.

## Derived objects

Derived objects are produced from session state and Core reasoning:

- `ReportSection`
  - A derived section within `InterviewReport` that maps session evidence and evaluation results to actionable findings.
- `EvaluationScore`
  - A calculated score for answer quality, evidence alignment, and STAR structure.
- `CoverageMap`
  - A derived representation of which evidence sources and claims were exercised by the session.

## Reusable objects

Reusable objects and contracts share common definitions across Core and module layers:

- `EvidenceReference`
  - The `{id,type}` contract used to link session objects to canonical evidence.
- `ReasoningContext`
  - The context passed to the reasoning engine for deterministic evaluation and report generation.
- `EvaluationRule`
  - A rule definition in Core that evaluates session answers, coverage, and compliance with the profile.
- `ArtifactDescriptor`
  - A metadata object used by the generator registry to create reports and summaries.

## Object classification summary

- Core objects: `CanonicalProfessionalProfile`, `InterviewPlan`, `InterviewQuestion`, `EvidencePackage`, `ClaimSet`, `TargetContext`
- Module-owned objects: `InterviewSession`, `InterviewQuestionInstance`, `InterviewAnswer`, `AnswerEvaluation`, `InterviewFeedback`, `InterviewReport`, `InterviewSummary`, `SessionMetrics`
- Derived objects: `ReportSection`, `EvaluationScore`, `CoverageMap`
- Reusable objects: `EvidenceReference`, `ReasoningContext`, `EvaluationRule`, `ArtifactDescriptor`

## Evidence contract

Every module-owned object that references professional knowledge must use the ADR-002 `{id,type}` evidence contract. This preserves the canonical profile as the single source of truth and prevents duplicated profile fragments within session state.
