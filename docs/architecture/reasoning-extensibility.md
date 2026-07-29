# Extensibility: Future Capabilities Built on the Reasoning Layer

The Professional Knowledge Reasoning Layer is designed as the shared
foundation for all future CareerOS capabilities. Every capability listed below
consumes the same Evidence Package and extends it with domain-specific rules
and overlays.

No capability requires AI to perform analysis. AI is always the last mile —
converting structured evidence into natural language.

---

## CV Tailoring

**How the reasoning layer is reused:** The standard Evidence Package provides
all skills, experiences, and strengths. A tailoring-specific overlay compares
the Evidence Package against a target job description to produce:

- A relevance-ranked list of experiences.
- Skills to emphasise and skills to de-emphasise.
- Suggested achievement selections per experience.
- A recommended CV structure order.

**New rules needed:** `requirement_matcher`, `achievement_selector`,
`section_reorder`.

**AI role:** Convert the tailored Evidence Package into a formatted CV
document.

---

## Cover Letter

**How the reasoning layer is reused:** The cover letter requires a focused
subset of the Evidence Package: strongest experience, most relevant skills,
and key strengths. The reasoning layer selects:

- The single best experience to lead the letter.
- 2–3 skills that differentiate the candidate.
- A personal value proposition derived from strength findings.

**New rules needed:** `opening_experience_selector`,
`differentiator_extractor`.

**AI role:** Expand the selected evidence into a narrative cover letter.

---

## Interview Preparation

**How the reasoning layer is reused:** Interview preparation requires
identifying areas of strength (to reinforce) and gaps (to address). The
reasoning layer produces:

- Expected questions per experience and skill.
- Weak areas that need preparation.
- Suggested story frameworks for key achievements.

**New rules needed:** `question_predictor` (maps skill to common interview
questions), `story_framework_matcher`, `preparation_priority_scorer`.

**AI role:** Generate mock interview questions and suggested response
frameworks from the evidence package.

---

## Career Gap Analysis

**How the reasoning layer is reused:** Gap analysis extends the Reasoning
Engine's Gap detector. It compares:

- Profile capabilities (from the Evidence Package) against:
  - Target role requirements (from a job description or competency matrix).
  - Industry benchmarks (from aggregated anonymized profiles).
  - Career stage expectations (from career_stage_classification).

**New rules needed:** `competency_matrix_comparator`,
`industry_benchmark_loader`, `gap_severity_calibrator`.

**AI role:** Summarise gaps in natural language and suggest remediation paths.

---

## Learning Recommendations

**How the reasoning layer is reused:** Learning recommendations build on gap
analysis. They identify missing competencies and map them to:

- Recommended courses, certifications, or projects.
- Estimated time to acquire each competency.
- Priority based on career trajectory.

**New rules needed:** `competency_to_learning_path_mapper`,
`learning_priority_scorer`.

**AI role:** Generate personalised learning path descriptions from the
structured recommendation data.

---

## Career Analytics

**How the reasoning layer is reused:** Career analytics aggregate Findings
across profiles, teams, or organisations. The same rules that analyse a
single profile also analyse populations:

- Average tenure by role type across an organisation.
- Most common skill gaps in a team.
- Career progression patterns by industry.

**New rules needed:** `population_aggregator`, `trend_detector`,
`benchmark_comparator`.

**AI role:** Generate executive summaries and visualisation descriptions from
aggregated data.

---

## Recruiter Reports

**How the reasoning layer is reused:** Recruiter reports rank and filter
candidates using rule-based criteria. The Evidence Package is the standardised
input for all candidates, enabling:

- Consistent candidate comparison.
- Automated screening against role requirements.
- Strengths/weaknesses summaries per candidate.

**New rules needed:** `candidate_ranker`, `requirement_scorer`,
`cultural_fit_indicator`.

**AI role:** Generate candidate summary reports from ranked Evidence Packages.

---

## Executive Dashboards

**How the reasoning layer is reused:** Dashboards visualise key metrics
derived from the Evidence Package. The same Findings power both AI-generated
narratives and chart-based dashboards:

- Skill distribution across the organisation.
- Tenure and retention patterns.
- Leadership pipeline health.

**New rules needed:** `metric_aggregator`, `visualisation_binding`.

**AI role:** Generate dashboard descriptions and annotations from aggregated
metrics.

---

## Architectural Principle: One Graph, Many Analyses

All future capabilities share the same architectural flow:

```
Knowledge Graph
       │
       ▼
Reasoning Engine (core rules)
       │
       ▼
Evidence Package (core)
       │
       ▼
Domain-specific overlay (rules + config)
       │
       ▼
Domain-specific Evidence Package
       │
       ▼
AI Provider
       │
       ▼
Generated Artifact
```

The core rules are always executed. Domain-specific overlays add, filter, or
re-weight findings. No capability bypasses the reasoning layer to read the
raw profile or graph directly.
