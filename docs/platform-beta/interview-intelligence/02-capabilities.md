# Interview Intelligence — 02. Capabilities

Three capabilities. Each one states what it does, how it stays deterministic-first, and which Core services it consumes (details in `03-core-integration.md`).

## A. Candidate Preparation

**Goal:** help a candidate rehearse with questions and answers that are grounded in their canonical profile.

| Sub-capability | Behavior |
|---|---|
| Technical questions | Generated from `Skill`s + `CONCEPT_TAXONOMY`/`extract_requirements` over the candidate's actual stack, plus role keywords |
| Behavioral questions | Generated from `Experience`/`Project` patterns (ownership, cross-functional work, conflict) |
| STAR questions | Target `Achievement`s and measurable outcomes; prompts require situation/task/action/result |
| Leadership questions | Target experiences/projects with leadership signals (team refs, scope, org/manager roles) |
| Project deep-dives | Target `Project` elements with `skillRefs`/`experienceRefs` and evidence |
| Weakness exploration | Driven by `ReasoningFindings` weaknesses/missing competencies — the same deterministic signals the profile already produces |
| Suggested answers | Claim-mediated outlines (`Claim → Evidence → Metric → Outcome`) selected deterministically; LLM only phrases, never invents |
| Evidence-backed answers | Every suggested answer carries `EvidenceCitation`s; candidate sees *what* to cite and *why it is citable* |

**Determinism first:** question *selection* and *targeting* are 100% deterministic over the canonical profile. LLM is used only for prose phrasing of an outline that was already fixed by Core reasoning.

**Output:** `PreparationGuide` persisted as an artifact through the artifact lifecycle.

## B. Interview Simulation

**Goal:** an interactive session that evaluates answers and coaches improvement.

| Sub-capability | Behavior |
|---|---|
| Interactive interview | `InterviewSession` walks `InterviewPlan` questions; state machine (`planned → in_progress → completed`) |
| Follow-up questions | Deterministic follow-up rules (dig deeper into a cited element, ask for a metric, ask for the STAR result) + optional LLM rephrase |
| Answer evaluation | `Evaluation` signals (`coversClaim`, `hasMetric`, `citesEvidence`, `followsStructure`, `matchesQuestionCompetencies`) computed deterministically; LLM commentary advisory |
| Feedback | Structured `Feedback` per criterion, `missing`, `improvementRecommendation`, `citations` |
| Improvement recommendations | Reuses `ReasoningFindings` (weak areas / missing competencies) plus simulation-specific signals (e.g. "your answers never cite evidence") |

**Determinism first:** signal computation is pure functions over the canonical profile + the answer text. Evaluations are qualitative levels (`weak | supported | strong | exceptional`), never stored numeric scores.

**Output:** `InterviewReport` (immutable per session).

## C. Recruiter Assistant

**Goal:** answer recruiter questions about a candidate, grounded exclusively in the canonical profile.

| Sub-capability | Behavior |
|---|---|
| "Which evidence supports Kubernetes expertise?" | Resolve skill → `Skill` element → `evidenceRefs` → canonical `evidence`; return cited evidence items |
| "What measurable achievements exist?" | Filter `Achievements` by measurable-outcome signals (reuse the measurability heuristic); summarize with metrics |
| "Which projects demonstrate AWS migration?" | Match project themes/skills against the migration concept (concept taxonomy aliases + skill refs) |
| "Has the candidate led technical teams?" | Leadership signals: experiences/projects with team/scope/manager evidence |
| "Summarize experience related to financial systems." | Domain match over experiences/projects/skills + evidence, then deterministic summary |
| General query | `RecruiterQuery` intent classification → deterministic `queryPlan` over `KnowledgeGraph` + evidence index |

**Groundedness rules:**
- Every `RecruiterAnswer` carries `citations` to canonical elements/evidence.
- Answers never fabricate; if the profile lacks data, the answer says so and suggests the profile gap.
- Recruiter output never exposes internal metadata (ADR-002 traceability + metadata-privacy guarantee).

**Determinism first:** query planning and evidence lookup are deterministic. LLM (optional) is restricted to rephrasing the assembled, cited facts — never adding facts.

## Cross-Capability Principles

1. **No profile writes.** None of the three capabilities mutates the canonical profile. Any profile improvement a prep/report suggests flows through the existing review workflow.
2. **No duplicate reasoning.** Weak areas, measurability, concept matching, and claim selection all delegate to Core.
3. **Qualitative evaluation.** No numeric scoring anywhere (ADR-003).
