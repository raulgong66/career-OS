# Reasoning Concepts

This document defines the core concepts used by the Professional Knowledge
Reasoning Layer. These are conceptual definitions only, intended to establish
a shared vocabulary for design and implementation.

---

## Finding

A single observation about the professional profile produced by a Rule.

Each Finding carries:
- **rule** — the Rule that produced it.
- **value** — the observed value (string, numeric, boolean, or structured).
- **evidence_nodes** — references to the Knowledge Graph nodes that support
  the Finding.
- **confidence** — a scalar 0.0–1.0 indicating confidence in the Finding.

Examples:
- Finding{rule: "years_of_experience", value: 8.5, confidence: 0.95}
- Finding{rule: "strongest_experience", value: "exp-qred-bank", confidence: 0.9}
- Finding{rule: "cloud_expertise", value: true, confidence: 0.85}

---

## Evidence

A specific data point from the Knowledge Graph that supports a Finding.

Evidence is always a reference to a graph node or edge property. It is not a
free-text description. The Evidence Package builder may enrich evidence with
summary text, but the core evidence is always a graph reference.

Examples:
- GraphNode{id: "skill-kubernetes", type: "skill", properties: {category: "Orchestration"}}
- GraphEdge{source: "exp-qred-bank", target: "skill-kubernetes", type: "USES_SKILL"}

---

## Evidence Set

A collection of related Evidence items grouped by theme.

Evidence Sets enable the Reasoning Engine to present coherent bundles of
supporting data rather than individual graph references. They are the unit
of attribution in generated artifacts.

Examples:
- Evidence Set{theme: "cloud_platforms", evidence: [AWS, GCP, Azure nodes]}
- Evidence Set{theme: "team_leadership", evidence: [experience nodes with management scope]}

---

## Rule

A deterministic function that accepts the Knowledge Graph and produces zero or
more Findings.

Rules are pure functions. They have no side effects, no state, no randomness.
They declare their input requirements and output type. Rules are registered in
the Rule Registry and executed by the Analysis Pipeline.

Rule interface (conceptual):
```
class Rule:
    name: str
    description: str
    input_types: list[NodeType]     # graph node types this rule reads
    def evaluate(graph: KnowledgeGraph) -> list[Finding]
```

Examples of Rules are cataloged in `reasoning-rules.md`.

---

## Rule Group

A logical grouping of related Rules.

Rule Groups enable the Analysis Pipeline to organise findings by domain
(e.g., "Skills", "Experience", "Education") and to express dependencies
between rules within a group.

Examples:
- Rule Group{domain: "skills", rules: [most_used_tech, skill_recency, skill_proficiency]}
- Rule Group{domain: "experience", rules: [strongest_experience, leadership, management]}
- Rule Group{domain: "tenure", rules: [total_years, years_per_skill, years_per_org]}

---

## Analysis Result

The complete output of one execution of the Reasoning Engine.

Contains all Findings produced by all enabled Rules, grouped by Rule Group.
The Analysis Result is an intermediate data structure. It is consumed by the
Evidence Package Assembler, not by AI providers directly.

```
AnalysisResult {
  profile_id: str
  generated_at: datetime
  rule_groups: list[RuleGroupResult]
  all_findings: list[Finding]
}
```

---

## Evidence Package

The output contract between the Reasoning Engine and AI providers.

A structured document containing pre-computed analytical results. AI providers
receive the Evidence Package as their sole input. The package contains no raw
profile data — only analysed, scored, and attributed findings.

Defined in detail in `evidence-package.md`.

---

## Recommendation

A suggested action or positioning based on the Evidence Package.

Recommendations are deterministic outputs of the Reasoning Engine, not AI
suggestions. They follow predefined logic: "If skill X is strong and skill Y
is missing, recommend upskilling in Y."

Each Recommendation carries:
- **type** — the category of recommendation (highlight, de-emphasize, acquire,
  improve).
- **priority** — high/medium/low.
- **rationale** — references to the Findings that produced it.
- **action** — what to do with the recommendation.

---

## Gap

A discrepancy between what the profile provides and what a target context
requires.

Gaps are produced by comparing Findings against a set of requirements (from a
job description, role profile, or target context). Each Gap identifies a
specific competency, skill, or qualification that is missing or insufficient.

```
Gap {
  requirement: str          # what is needed
  actual: str | null        # what the profile provides (null if absent)
  severity: str             # critical, major, minor
  supporting_evidence: list[Finding]
}
```

---

## Confidence

A scalar 0.0–1.0 representing the Reasoning Engine's certainty about a
Finding.

Confidence is computed from:
- **Source reliability.** Direct source data > inferred > derived.
- **Evidence quantity.** More supporting graph nodes = higher confidence.
- **Recency.** More recent data is weighted higher.
- **Consistency.** Data corroborated by multiple sources scores higher.

Confidence is not probability. It is a deterministic score based on objective
properties of the evidence graph. Two runs with the same graph produce the
same confidence values.
