# Evidence Package

## Overview

The Evidence Package is the output contract between the Reasoning Engine and
every AI provider. It contains pre-computed, deterministic analytical results.
AI providers receive the Evidence Package as their sole input for artifact
generation.

## Why AI Consumes Evidence Instead of the Raw Profile

| Concern | Raw Profile | Evidence Package |
|---|---|---|
| **Token cost** | Full profile with all entities, references, and metadata | Compact, pre-analysed summary |
| **Hallucination risk** | AI must compute its own analytical conclusions | AI receives pre-computed facts; no analytical hallucination possible |
| **Determinism** | Same profile + same prompt can produce different results | Same profile always produces the same Evidence Package |
| **Testability** | Cannot unit test prompt logic | Every Rule is independently testable |
| **Provider portability** | Each provider re-implements analysis | One Evidence Package serves all providers |
| **Auditability** | No traceability from artifact to analysis | Every statement links to a Rule and graph nodes |
| **Cacheability** | Entire profile must be re-sent each time | Evidence Package is cacheable until profile changes |

## Package Structure

```yaml
evidence_package:
  meta:
    generated_at: "2026-07-29T12:00:00Z"
    profile_id: "person-raul-gongora"
    profile_version: "1.0.0"
    reasoning_version: "1.0.0"
    rule_count: 18
    finding_count: 47

  candidate_summary:
    full_name: "Raul Gongora"
    current_title: "Senior DevSecOps Engineer"
    current_organization: "Qred Bank"
    total_years_of_experience: 8.5
    highest_education: "M.Sc. in Computer Science"
    highest_education_institution: "KTH Royal Institute of Technology"
    career_stage: "Senior"
    top_skills:
      - name: "Python"
        category: "Programming Language"
        evidence_count: 3
      - name: "Kubernetes"
        category: "Orchestration"
        evidence_count: 2
      - name: "AWS"
        category: "Cloud"
        evidence_count: 2
    skill_count: 12
    experience_count: 4
    organization_count: 3

  relevant_experiences:
    - experience_id: "exp-qred-bank"
      title: "Senior DevSecOps Engineer"
      organization: "Qred Bank"
      organization_id: "org-qred-bank"
      date_range:
        start: "2022-03"
        end: "2025-01"
        is_current: false
      duration_years: 2.8
      relevance_score: 0.95
      relevance_rationale: "Most recent and longest-tenured senior role"
      engagement_type: "Full-time"
      scope_summary: "Full stack developer"
      key_achievements:
        - achievement_text: "Led cloud migration"
          source_experience_id: "exp-qred-bank"
      technologies_used:
        - name: "Python"
          category: "Programming Language"
          evidence_id: "exp-qred-bank-skill-python"
        - name: "Kubernetes"
          category: "Orchestration"
          evidence_id: "exp-qred-bank-skill-kubernetes"
      skills_demonstrated:
        - "DevSecOps"
        - "Cloud Architecture"
        - "Team Leadership"
      classification:
        is_leadership: true
        is_management: false
        is_technical_ic: true

    - experience_id: "exp-kth"
      title: "Teaching Assistant"
      organization: "KTH Royal Institute of Technology"
      organization_id: "org-kth"
      date_range:
        start: "2019-09"
        end: "2020-06"
        is_current: false
      duration_years: 0.8
      relevance_score: 0.4
      relevance_rationale: "Academic role with relevant technology exposure"
      technologies_used:
        - name: "Java"
          category: "Programming Language"
          evidence_id: "exp-kth-skill-java"
      skills_demonstrated:
        - "Teaching"
        - "Java"
      classification:
        is_leadership: false
        is_management: false
        is_technical_ic: true

  matching_skills:
    - skill_name: "Python"
      skill_id: "skill-python"
      category: "Programming Language"
      proficiency: "Advanced"
      years_of_experience: 5.2
      last_used: "2025-01"
      experience_count: 3
      evidence_count: 3
      confidence: 0.95
    - skill_name: "Kubernetes"
      skill_id: "skill-kubernetes"
      category: "Orchestration"
      proficiency: "Advanced"
      years_of_experience: 2.8
      last_used: "2025-01"
      experience_count: 2
      evidence_count: 2
      confidence: 0.9
    - skill_name: "Java"
      skill_id: "skill-java"
      category: "Programming Language"
      proficiency: "Proficient"
      years_of_experience: 0.8
      last_used: "2020-06"
      experience_count: 1
      evidence_count: 1
      confidence: 0.85

  education:
    - education_id: "edu-kth-m-sc"
      institution: "KTH Royal Institute of Technology"
      institution_id: "org-kth"
      degree: "M.Sc."
      field_of_study: "Computer Science"
      date_range:
        start: "2018"
        end: "2021"
        is_current: false
      relevance: "Direct field match"
      relevance_score: 1.0

  strengths:
    - category: "Technical Leadership"
      description: "Demonstrated DevSecOps leadership at Qred Bank"
      supporting_evidence:
        - finding_id: "leadership_evidence"
        - finding_id: "strongest_experience"
      confidence: 0.9
    - category: "Cloud & Infrastructure"
      description: "Multiple cloud platforms and orchestration tools"
      supporting_evidence:
        - finding_id: "cloud_expertise"
        - finding_id: "infrastructure_evidence"
      confidence: 0.85
    - category: "Programming"
      description: "Strong programming foundation across multiple languages"
      supporting_evidence:
        - finding_id: "programming_language_evidence"
      confidence: 0.9

  weaknesses:
    - category: "Management Experience"
      description: "No explicit people management responsibility detected"
      supporting_evidence:
        - finding_id: "management_evidence"
      confidence: 0.95
    - category: "Industry Breadth"
      description: "Experience concentrated in a single industry"
      supporting_evidence:
        - finding_id: "industry_coverage"
      confidence: 0.7

  missing_competencies:
    - competency: "Direct people management"
      required_level: "Experienced"
      actual_level: "None detected"
      gap_severity: "major"
      source: "management_evidence rule"
    - competency: "Budget ownership"
      required_level: "Experienced"
      actual_level: "None detected"
      gap_severity: "major"
      source: "management_evidence rule"

  supporting_evidence:
    - evidence_id: "exp-qred-bank-skill-python"
      type: "experience_to_skill"
      source_experience_id: "exp-qred-bank"
      source_skill_id: "skill-python"
      summary: "Python used at Qred Bank as primary development language"
    - evidence_id: "exp-qred-bank-skill-kubernetes"
      type: "experience_to_skill"
      source_experience_id: "exp-qred-bank"
      source_skill_id: "skill-kubernetes"
      summary: "Kubernetes used at Qred Bank for container orchestration"

  recommendations:
    - type: "highlight"
      description: "Position DevSecOps leadership as primary differentiator"
      priority: "high"
      rationale: "Strongest experience combines security, cloud, and leadership"
    - type: "de_emphasize"
      description: "Teaching Assistant role should be secondary emphasis"
      priority: "medium"
      rationale: "Academic role with lower relevance to senior industry positions"
    - type: "acquire"
      description: "Consider pursuing people management opportunities"
      priority: "low"
      rationale: "Missing management evidence limits executive career progression"

  rule_summary:
    total_rules_executed: 18
    total_findings_produced: 47
    rules_by_group:
      experience: 5
      skills: 7
      education: 2
      tenure: 3
      analysis: 1
    execution_time_ms: 12
```

## Schema Versioning

The Evidence Package schema is versioned independently of the canonical profile
schema. Version is declared in `meta.reasoning_version`. Breaking changes to
the evidence package schema increment the major version. Additive changes
(fields) increment the minor version.

## Extension Points

- **Target context overlay.** When a target context (job description, role
  profile) is provided, the Evidence Package includes a `target_context`
  section with matched requirements vs. profile capabilities.
- **Custom rules.** Organizations may inject custom rules that produce
  additional findings in the Evidence Package. These appear under a
  `custom_findings` namespace to prevent collision with core rules.
- **Provider hints.** The Evidence Package may include optional hint fields
  for specific AI providers (e.g., token budgets, preferred output structure)
  without breaking compatibility for other providers.
