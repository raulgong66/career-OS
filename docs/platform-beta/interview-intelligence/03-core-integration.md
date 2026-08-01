# Interview Intelligence — 03. Core Integration

For every capability, the Core services it reuses and why there is **no duplicated logic**.

## Reused Core Services

| Core service | Path / model | Reuse |
|---|---|---|
| Canonical Profile | `schemas/profile.schema.json`, `careeros/profile_loader.py`, `careeros/profile_repository.py` | Grounding for every question, answer, and recruiter response |
| Validation | `careeros/validator.py`, `careeros/schema_loader.py` | Validate any new persisted module entities; validate profile reads |
| Knowledge Graph | `careeros/knowledge/` (`KnowledgeGraph`, `GraphNode`, `GraphEdge`) | Skills→experiences→projects→achievements→evidence navigation for targeting and recruiter queries |
| Reasoning Engine | `careeros/reasoning/` (`ReasoningEngine`, `RuleRegistry`, `ReasoningFindings`) | Weak areas, missing competencies, strengths for prep guides, feedback, and reports |
| Rule Registry | `careeros/reasoning/registry.py` | Register *new interview-specific rules* rather than re-implementing analysis |
| Evidence model | ADR-002, `evidence` + `evidenceRefs`/`relatedRefs` | `EvidenceCitation` grounding; recruiter evidence queries |
| Claim model | ADR-003, `interview_answers` target context | Suggested answers; claim selection for answers |
| Achievements | canonical `achievements` | STAR questions, measurable-outcome evaluation, recruiter achievement queries |
| Measurability heuristic | `careeros/resolution.py` (encapsulates the recommendation-rules heuristic) | "Is the answer's outcome measurable?" — reused, never re-implemented |
| Concept / requirement matching | `careeros/optimizer.py` (`CVOptimizer.extract_requirements`, `CONCEPT_TAXONOMY`, `RequirementConcept`) | Role keywords, project-theme matching (e.g. "AWS migration") |
| Export Contract | `careeros/export_contract.py` (`ExportContractBuilder`, `ExportSource`) | Build preparation guides / interview reports as documents |
| Artifact lifecycle | canonical `artifacts` (`status` current/stale), regeneration policy | Persist `PreparationGuide` / `InterviewReport`; stale on profile change; explicit regeneration only |
| Artifact Templates | `careeros/artifact_templates.py` (`TemplateRegistry`) | Register `INTERVIEW_PREPARATION` / `INTERVIEW_REPORT` templates |
| Generation pipeline | `careeros/pipelines.py` (`generate_artifact`) | Render prep/report artifacts through the existing pipeline |
| Review workflow | acquisition `review_callback` + `ProfileState` (staging/canonical/archived) | Any profile change suggested by interview feedback goes through human review |

## Per-Capability Mapping

### A. Candidate Preparation

| Need | Core service used | Duplication avoided |
|---|---|---|
| Generate technical questions for the candidate's stack | Skills + `CVOptimizer.extract_requirements` | Not re-implementing requirement extraction |
| Behavioral / leadership / project questions from real history | Knowledge Graph over experiences/projects | Not re-implementing entity navigation |
| Weakness-driven questions | `ReasoningFindings` weaknesses / missing competencies | Not re-implementing profile analysis |
| Suggested answers | ADR-003 Claims (selected for `interview_answers`) + Evidence + Achievements | Not inventing a new claim store |
| Measurable-outcome answers | measurability heuristic (via `careeros/resolution.py`) | Not re-implementing measurability detection |
| Prep guide document | `ExportContractBuilder` + `TemplateRegistry` + `generate_artifact` + artifact lifecycle | Not duplicating document generation |

### B. Interview Simulation

| Need | Core service used | Duplication avoided |
|---|---|---|
| Weak-area-based follow-ups | `ReasoningFindings` | Not re-analyzing the profile |
| Answer measurability check | measurability heuristic | Reused as in prep |
| Evidence-grounding check | Evidence model + reference contract | Not re-implementing traceability |
| Improvement recommendations | `ReasoningFindings` + Rule Registry (new interview rules) | Extends, never replaces, Core reasoning |
| Interview report document | Export pipeline + artifact lifecycle | Reused |

### C. Recruiter Assistant

| Need | Core service used | Duplication avoided |
|---|---|---|
| "Evidence supports Kubernetes" | Skill → `evidenceRefs` → evidence items (Knowledge Graph + evidence model) | Not re-implementing an evidence index |
| "Measurable achievements?" | Achievements + measurability heuristic | Reused |
| "AWS migration projects?" | Concept taxonomy + skill/project matching | Not re-implementing concept matching |
| "Led technical teams?" | Leadership signals over experiences/projects + reasoning findings | Reuses reasoning findings |
| "Financial systems experience?" | Domain matching via concept taxonomy + evidence | Not re-implementing matching |
| Grounded answers with citations | ADR-002 reference contract | Reused traceability contract |

## "No Duplicate Reasoning / No Duplicate Knowledge" Guarantees

1. **One profile.** Every module object references canonical elements by id; no parallel copy of professional facts.
2. **One reasoning engine.** New interview rules register in `RuleRegistry`; the module never runs its own profile analysis.
3. **One evidence/claim model.** ADR-002/ADR-003 are the only sources of "how do we know" and "what are we saying".
4. **One export pipeline.** Prep guides and reports are artifacts; they reuse `ExportContractBuilder`, templates, generators, and lifecycle.
5. **One review path.** Profile changes are only written by Core services under the review workflow.

## Notable Core Gaps to Fill Before Implementation

- **Public measurability API:** the measurability heuristic lives behind the Resolution Engine; expose a public helper (`careeros.resolution.is_measurable`) so interview evaluation can reuse it without reaching into private symbols.
- **Claim model not yet implemented:** suggested answers depend on ADR-003's claim layer; until then, suggested answers can source directly from achievements/evidence with claim-shaped outlines.
- **Recruiter query index:** deterministic intent classification is module-owned but must build on `KnowledgeGraph` navigation, not a new index.
