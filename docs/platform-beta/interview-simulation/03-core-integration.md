# Interview Simulation Core Integration

Interview Simulation is a Core consumer. It reuses existing platform services rather than introducing a parallel reasoning path.

## KnowledgeGraph

Interview Simulation uses the Core `KnowledgeGraph` to query the canonical profile, evidence relationships, and claim structure. The session engine does not duplicate profile data; it references canonical evidence and claim identifiers and relies on the graph for context.

## ReasoningEngine

The `ReasoningEngine` is used for deterministic evaluation of answers, coverage checks, and consistency analysis. Interview Simulation delegates evaluative logic to Core reasoning rather than implementing separate inference pathways.

## RuleRegistry

Evaluation and session validation rules are registered in Core’s `RuleRegistry`. Examples include:

- question coverage rules
- evidence sufficiency rules
- STAR structure rules
- profile consistency rules
- session state transition validation

This keeps policy centralized and avoids duplicated rule logic.

## Evidence Model

The session layer stores evidence references as ADR-002 `{id,type}` objects. Interview answers, feedback, and report assertions are all traceable back to canonical evidence items.

## Claim Model

Interview Simulation uses the ADR-003 claim model to ensure answer validation and reports align with the same claim space as the rest of the platform. Feedback and evaluations refer to claim identifiers when describing profile consistency.

## ExportContract

Report and summary generation reuse the existing Core `ExportContract` model. Interview Simulation produces artifact descriptors that flow through the same export pipeline used by other platform artifacts.

## Generator Registry

Interview reports and summaries are produced through the Core generator registry. This preserves consistent artifact generation patterns and allows the module to benefit from existing generators, templates, and export formats.

## AI Provider abstraction

AI is used only as an enrichment layer for Interview Simulation.

- AI may produce guidance text, feedback phrasing, or report language.
- AI does not determine correctness.
- Deterministic evaluation and rule-based scoring remain authoritative.

The module consumes the provider abstraction defined in ADR-006 to keep provider-specific details out of the session engine.

## Resolution Engine

If session activity proposes changes to the canonical profile, those proposals are treated as advisory and must pass through Core’s resolution path. Interview Simulation does not mutate the profile directly.

The module may log suggested profile updates, but any attachment to the canonical profile must be made through Core resolution and human review.

## Target Contexts

Interview Simulation reuses existing Core target contexts from `InterviewPlan` and evidence selection. The session engine shapes prompts and evaluation contexts from the same target definitions used by preparation guide generation.

## InterviewPlan

The existing `InterviewPlan` is the template for Interview Simulation. The module consumes it directly, reusing question definitions, evidence expectations, and target context metadata.

## Integration summary

Interview Simulation is designed as a consumer of Core services:

- It uses `KnowledgeGraph` for canonical context.
- It uses `ReasoningEngine` for deterministic evaluation.
- It uses `RuleRegistry` for validation policy.
- It uses ADR-002 and ADR-003 contract objects for evidence and claims.
- It uses `ExportContract` and generator registry for report artifacts.
- It uses ADR-006 provider abstractions for AI enrichment.
- It uses the Resolution Engine for any proposed profile changes.

This architecture avoids duplicated reasoning and keeps the session module aligned with the Core platform foundation.