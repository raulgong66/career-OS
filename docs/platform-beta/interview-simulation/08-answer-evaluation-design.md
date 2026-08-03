# Interview Simulation Answer Evaluation Design

This document defines the architecture for the M1.17.4 Answer Evaluation Engine within Interview Simulation. It freezes the evaluation responsibilities, public contract, integration points, runtime boundaries, and extension surfaces for future implementation.

## Purpose

The Answer Evaluation Engine deterministically analyzes interview answers produced during a session and generates structured evaluation signals and feedback recommendations. It is a Core consumer that reuses existing evidence and claim models, measurability support, and rule-based reasoning without introducing new profile knowledge or AI-generated correctness judgments.

## Evaluation philosophy

The engine must be:

- Deterministic
  - The same input produces the same evaluation output every time.
  - Evaluation behavior is driven by explicit rules and canonical model references.
- Explainable
  - Every evaluation signal is traceable to evidence, claims, structure, or measurability checks.
  - Feedback items describe why an answer is strong, weak, or inconsistent.
- Reproducible
  - Evaluation results can be reconstructed from the same session state, answer content, and rule set.
  - No wall-clock or provider-specific randomness influences outcomes.
- Provider-independent
  - The engine does not depend on any AI provider implementation.
  - Any AI enrichment is a separate future layer.

## Engine responsibilities

The Answer Evaluation Engine owns:

- validating an `InterviewAnswer` against the active question and session context
- checking coverage of the expected question intent or claim requirements
- validating evidence citations against ADR-002 canonical references
- validating answers against ADR-003 claim expectations
- analyzing answer structure using STAR / narrative conventions
- assessing measurability using Core measurability services
- checking internal consistency within the answer and relative to session metadata
- producing deterministic feedback signals and evaluation summaries

The engine must never own:

- canonical profile knowledge
- interview question generation or planning
- session lifecycle orchestration
- AI-generated correctness judgments
- provider-specific scoring engines
- persistence, transport, or frontend rendering
- raw profile mutation or canonical profile updates

## Evaluation pipeline

The Answer Evaluation Engine processes answers through a deterministic pipeline:

- `InterviewAnswer`
- Coverage Check
- Evidence Validation
- Claim Validation
- STAR Analysis
- Measurability Analysis
- Consistency Analysis
- Deterministic Feedback

### Pipeline stages

- Coverage Check
  - Verifies that the answer engages the expected intent or competencies of the question.
  - References the question's competencies and context requirements.
- Evidence Validation
  - Verifies that cited evidence references conform to ADR-002 `{id,type}`.
  - Confirms that evidence citations are canonical profile references, not session-owned fragments.
- Claim Validation
  - Verifies alignment with ADR-003 claim requirements for the question or target role.
  - Uses canonical claim references rather than ad hoc scoring criteria.
- STAR Analysis
  - Checks whether the answer follows a structured response pattern relevant to the question type.
  - Produces qualitative structure signals, not numeric scores.
- Measurability Analysis
  - Uses Core measurability APIs to determine whether the answer includes measurable achievements.
  - Preserves the qualitative evaluation model by mapping measurable content to supporting feedback.
- Consistency Analysis
  - Detects internal contradictions, unsupported claims, or mismatched evidence.
  - Verifies that answer assertions are consistent with the current session and canonical references.
- Deterministic Feedback
  - Produces structured evaluation signals and recommended improvement guidance.
  - Does not generate final narrative prose; it produces advisory outputs for a future enrichment layer.

## Integration points

The Answer Evaluation Engine reuses existing CareerOS components:

- Measurability Core
  - Consumes the public `is_measurable` or equivalent API to determine measurable answer components.
- Resolution Engine
  - Uses canonical resolution services to map evidence citations and claim references to profile entities.
- Evidence Model (ADR-002)
  - All evidence citations and references are canonical `{id,type}` links.
- Claim Model (ADR-003)
  - Claim expectations are validated against the professional claim model, not ad hoc scores.
- Rule Registry
  - Evaluation rules are defined and discovered through the shared rule registry.

The engine must avoid duplicated reasoning by reusing existing Core services wherever possible and by treating Core as the authoritative source for evidence and claim semantics.

## Public contract

### Inputs

- `InterviewAnswer`: the candidate answer object from the current session
- `InterviewQuestionInstance`: the instantiated question context for the answer
- `InterviewSession`: optional session context when answer-level evaluation requires session metadata or history
- `RuleRegistry`: the deterministic rule set used for evaluation

### Outputs

- `AnswerEvaluation`: a structured vector of deterministic evaluation signals
- `InterviewFeedback`: advisory feedback items derived from evaluation results
- `EvaluationSummary`: session-level summary of coverage, evidence, claim alignment, and measurability

### Exceptions

The engine raises explicit domain-specific exceptions for validation failures:

- `InvalidAnswerError`
  - Raised when the answer input is malformed or empty.
- `InvalidQuestionError`
  - Raised when the question context is missing or mismatched.
- `MissingEvidenceReferenceError`
  - Raised when cited evidence references are invalid or not canonical.
- `InvalidClaimError`
  - Raised when claim validation cannot proceed due to missing claim metadata.
- `EvaluationPreconditionError`
  - Raised when required context or Core services are unavailable.

### Module boundaries

- The engine depends on Core and shared evaluation abstractions only.
- It must not depend on frontend, REST APIs, persistence, or provider SDKs.
- It may consume provider-agnostic abstractions for future enrichment, but these are external extension points.

## Runtime boundaries

The architecture separates runtime responsibilities clearly:

- Session Engine
  - owns session lifecycle, question sequencing, answer capture, and session state transitions.
- Evaluation Engine
  - owns deterministic answer analysis, rule application, evidence validation, claim validation, and feedback signals.
- AI Enrichment (future)
  - owns advisory language generation, narrative framing, and external provider interaction.

The Evaluation Engine consumes answers and session context but does not drive session state transitions or produce user-facing prose.

## Extension points

The Answer Evaluation Engine exposes explicit extension surfaces for future integration:

- AI Feedback (M1.17.5)
  - A future layer consumes evaluation signals and transforms them into advisory narrative.
- Analytics
  - Evaluation results may emit anonymized metrics and event payloads for dashboards.
- REST API
  - External controllers may expose evaluation operations as service endpoints.
- Persistence
  - External runtime storage layers may persist evaluation results, feedback artifacts, and session summaries.

## Readiness

This document defines the M1.17.4 Answer Evaluation architecture without implementation detail. It is ready for subsequent implementation once the evaluation engine contract and rules are formalized in code.
