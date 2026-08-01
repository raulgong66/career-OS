# Interview Intelligence — 01. Domain Model

## Purpose

Define the domain objects of the Interview Intelligence module. The module is a **Core consumer**: it introduces new objects only where Core does not already provide one, and it references Core objects (Canonical Profile, Evidence, Achievements, Claims, Reasoning Findings) through their existing identity/reference contracts — never by duplicating them.

## Core Objects Referenced (not duplicated)

| Object | Source | Used for |
|---|---|---|
| `CanonicalProfile` | `schemas/profile.schema.json` | Single source of truth for every grounding decision |
| `Person`, `Experience`, `Project`, `Skill`, `Education`, `Certification` | canonical profile | Question targeting, answer grounding, recruiter answers |
| `Achievement` | canonical profile (`achievements`) | STAR answers, measurable-outcome evidence |
| `Evidence` | ADR-002 model (`evidence` + `evidenceRefs`/`relatedRefs`) | `EvidenceCitation`, recruiter evidence queries |
| `Claim` | ADR-003 model (design) | Suggested answers, claim selection for `interview_answers` context |
| `KnowledgeGraph` / `GraphNode` / `GraphEdge` | `careeros/knowledge/` | Graph navigation for question targeting and recruiter queries |
| `ReasoningFindings` / `ReasoningResult` | `careeros/reasoning/models.py` | Answer evaluation signals, prep-guide weak areas |
| `ExportSource` / `ExportContract` | `careeros/export_contract.py` | Building preparation-guide and report documents |
| `Artifact` (with `status`) | canonical profile (`artifacts`) | Persisting preparation guides / interview reports via the artifact lifecycle |
| `TargetContext` | canonical profile (`targetContexts`) | Claim targeting for `interview_answers` context |

## Module-Owned Domain Objects

### Question layer

**InterviewQuestion** — a typed, self-contained question bound to profile context.
- `id`, `type` (see below), `prompt`, `difficulty`, `competencyRefs` (`[{id, type: "skill"|"competency"}]`)
- Optional `contextRefs` — profile elements the question targets (`[{id, type}]` following the ADR-002 reference contract)
- Optional `expected` — the deterministic expectations used at evaluation time (structured; not free text only)
- Optional `templateRef` — the `QuestionTemplate` that produced it (traceability)

**QuestionType** — enum: `technical | behavioral | star | leadership | project_deep_dive | weakness | recruiter_query`.

**QuestionTemplate** — a parameterized generator (the analog of `ArtifactTemplate`).
- `template_id`, `type`, `prompt_pattern`, `placeholders` (bound to canonical elements at generation time), `difficulty_default`
- Responsible for *instantiating* `InterviewQuestion`s from a profile + target; it holds no profile data.

**Competency** — a reusable capability identifier.
- `id`, `label`, `skillRefs` (link to canonical `skills`), `aliases` (reuse the optimizer's alias vocabulary where applicable)
- Derived deterministically; not a new knowledge store. A competency is a **view over** skills + `CONCEPT_TAXONOMY`, never a parallel skill registry.

### Session layer

**InterviewSession** — a planned or in-progress interview.
- `id`, `mode` (`candidate_prep | simulation | recruiter_query`), `status` (`planned | in_progress | completed`)
- `profileId`, `targetRole` (optional), `competencyRefs`, `planRef`
- `questionIds`, `startedAt`, `completedAt`

**Answer** — a candidate response to a question within a session.
- `id`, `sessionId`, `questionId`, `text`, `answeredAt`
- Deterministic analysis results derived at evaluation time (not stored as a parallel model).

### Evaluation layer

**EvidenceCitation** — a grounded reference attached to an answer or feedback.
- `id`, `sourceRef` (`{id, type}` to a canonical element), optional `evidenceRefs` (`[{id}]` to canonical evidence)
- Optional `quote` — verbatim excerpt; never internal metadata (ADR-002 traceability + metadata-privacy guarantee)

**Feedback** — structured, per-question evaluation.
- `id`, `questionId`, `answerId`, `criteriaResults` (one entry per criterion, see evaluation)
- `missing` — what the answer lacked (e.g. metric, evidence, STAR structure)
- `improvementRecommendation` — reusable, deterministic guidance text
- `citations` — `EvidenceCitation`s detected in (or suggested for) the answer
- Deliberately **no stored numeric score** — consistent with ADR-003's qualitative approach.

**Evaluation** — the assessment engine's output shape (not a stored object).
- Per-criterion qualitative levels `weak | supported | strong | exceptional` (mirrors ADR-003 claim strength)
- Deterministic signals: `coversClaim`, `hasMetric`, `citesEvidence`, `followsStructure`, `matchesQuestionCompetencies`
- Optional LLM commentary is **advisory only** and never the source of truth.

### Document / planning layer

**InterviewPlan** — an ordered set of questions targeting a role/competency objective.
- `id`, `profileId`, `targetRole`, `competencyRefs`, `questionIds`, `focusWeakAreas` (from `ReasoningFindings`)

**SuggestedAnswer** — a candidate-visible structured answer outline.
- `id`, `questionId`, `outline` (claim → evidence → metric → outcome), `claimRefs` (ADR-003 claims), `evidenceRefs`, `achievementRefs`
- Always grounded in canonical profile; LLM only rephrases pre-selected, deterministic material.

**PreparationGuide** — a consumable document for the candidate.
- `id`, `profileId`, `targetRole`, `sections` (questions, suggested answers, evidence to rehearse, weak areas)
- Produced via `ExportContractBuilder` + a registered template; persists as an `Artifact` with lifecycle `status`.

**InterviewReport** — immutable outcome of a completed simulation.
- `id`, `sessionId`, per-question `Feedback`s, aggregate `Evaluation`, `strengths`/`weaknesses` (from reasoning + simulation), `recommendations`

### Recruiter layer

**RecruiterQuery** — a natural-language question from a recruiter.
- `id`, `text`, `intent` (deterministic classification: `evidence_for_skill | measurable_achievements | project_theme | leadership_experience | domain_experience | other`)
- `queryPlan` — the deterministic execution plan over canonical profile (index lookups, graph navigation)

**RecruiterAnswer** — the grounded response.
- `id`, `queryId`, `summary` (factual), `citations` (`EvidenceCitation`s / source refs), `confidenceInputs` (evidence verification status mix per ADR-002)
- Never contains internal reasoning metadata; never fabricates facts not in the profile.

## Relationships

```
CanonicalProfile ───► InterviewPlan ───► [InterviewSession] ──► Answer
       │  ▲                                  │                     │
       │  │ (grounding)                      ▼                     ▼
       │  └── Evidence/Claim/Achievement   Feedback ◄── Evaluation
       │                                   │ ▲
       │                                   ▼ │ (citations)
       │                            EvidenceCitation
       │
       ├──► QuestionTemplate ──► InterviewQuestion ──► SuggestedAnswer
       │
       └──► RecruiterQuery ──► RecruiterAnswer
```

## Ownership Rules

1. Module objects never become the source of truth for professional facts. Facts live in the canonical profile (+ evidence/claims layers).
2. All references to canonical elements use the ADR-002 reference contract (`{id, type}` / `evidenceRefs`).
3. Qualitative levels, never numeric scores (ADR-003 consistency).
4. No `Review`, `Claim`, or `Evidence` re-implementations — those remain Core-owned.
