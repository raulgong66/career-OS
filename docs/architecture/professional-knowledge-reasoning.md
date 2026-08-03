# Professional Knowledge Reasoning

## Overview

The Professional Knowledge Reasoning Layer sits between the Knowledge Graph
and AI providers. It performs deterministic analysis of the professional
profile and produces a structured Evidence Package that every AI provider
consumes.

## Architecture Flow

```
  Knowledge Acquisition
         │
         ▼
   Canonical Profile
         │
         ▼
    Knowledge Graph          ← M5 (existing)
         │
         ▼
   Reasoning Engine          ← M6 (new)
         │
         ▼
   Evidence Package          ← M6 (new)
         │
         ▼
     AI Provider             ← M7+ (future)
         │
         ▼
  Generated Artifact
```

## Layer Responsibilities

### 1. Knowledge Acquisition (M0–M4, existing)

Ingests external source documents (DOCX, PDF, Markdown), extracts structured
data, normalizes entities, and produces a validated canonical profile.
*Owned by the Professional Knowledge Acquisition Framework.*

### 2. Canonical Profile (M1, existing)

The single source of truth: a validated YAML document conforming to the
canonical profile schema. Contains person, experiences, skills, education,
organizations, certifications, and evidence. *Owned by the core library.*

### 3. Knowledge Graph (M5, existing)

An immutable, in-memory directed graph built from the canonical profile.
Provides navigable relationships (HAS_EXPERIENCE, USES_SKILL, AT_ORGANIZATION)
and a query API. *Owned by `careeros/knowledge/`.*

### 4. Reasoning Engine (M6, new)

The deterministic core of the reasoning layer. Responsibilities:

- **Rule Registry.** Maintains a collection of registered Rule implementations.
  Each Rule declares its input requirements (graph node types it reads) and
  output type (Findings it produces).
- **Analysis Pipeline.** Iterates registered rules in dependency order, passes
  the Knowledge Graph to each, and collects Findings.
- **Evidence Set Builder.** Groups related Findings into Evidence Sets
  (e.g., all skill-related findings, all experience-related findings).
- **Gap Detector.** Compares Findings against requirements (from a target
  context or job description) to produce Gap records.
- **Confidence Scorer.** Assigns a confidence value to each Finding based on
  evidence quality, recency, and source reliability.
- **Evidence Package Assembler.** Composes Findings, Evidence Sets, Gaps, and
  Recommendations into the final Evidence Package.

The Reasoning Engine has no knowledge of AI providers. It operates exclusively
on the Knowledge Graph and a configuration of enabled rules.

### 5. Evidence Package (M6, new)

The output contract between the Reasoning Engine and every AI provider.
A structured document containing pre-computed analytical results. AI providers
receive the Evidence Package as their sole input. They do not read the raw
profile or Knowledge Graph.

Sections: Candidate Summary, Relevant Experiences, Matching Skills, Education,
Strengths, Weaknesses, Missing Competencies, Supporting Evidence,
Recommendations. *Defined in detail in `evidence-package.md`.*

### 6. AI Provider (M7+, future)

Converts the Evidence Package into a natural language artifact. The AI's
responsibility is limited to:

- Formatting structured findings into fluent prose.
- Applying tone, voice, and audience-specific style.
- Structuring output according to artifact type (CV, cover letter, etc.).
- No analytical reasoning. No fact-finding. No data discovery.

Multiple providers can consume the same Evidence Package, differing only in
generation quality, cost, or latency.

### 7. Generated Artifact (M7+, future)

The final output: CV, cover letter, portfolio, interview brief, or other
professional document. Every claim in the artifact traces back through the
Evidence Package to a specific Rule and Knowledge Graph node.

## Rule Execution Model

```
                  ┌──────────────┐
                  │   Profile    │
                  │ Knowledge    │
                  │   Graph      │
                  └──────┬───────┘
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
      ┌──────────┐ ┌──────────┐ ┌──────────┐
      │  Rule A  │ │  Rule B  │ │  Rule C  │
      │ (tenure) │ │ (recency)│ │ (skills) │
      └────┬─────┘ └────┬─────┘ └────┬─────┘
           │            │            │
           ▼            ▼            ▼
      ┌─────────────────────────────────────┐
      │         Findings Collection          │
      ├─────────────────────────────────────┤
      │ Finding{rule, value, evidence, conf} │
      │ Finding{rule, value, evidence, conf} │
      └─────────────────┬───────────────────┘
                        │
                        ▼
      ┌─────────────────────────────────────┐
      │        Evidence Package Builder      │
      └─────────────────┬───────────────────┘
                        │
                        ▼
      ┌─────────────────────────────────────┐
      │           Evidence Package           │
      └─────────────────────────────────────┘
```

## Design Principles

1. **Determinism first.** Every Rule produces the same output for the same
   graph. No randomness, no model inference, no heuristics that change between
   runs.
2. **Composable rules.** Rules are independent and stateless. They can be
   added, removed, reordered, or toggled without affecting other rules.
3. **Evidence traceability.** Every Finding carries references to the specific
   graph nodes that produced it. This enables the "why" question for every
   statement in a generated artifact.
4. **Provider agnosticism.** The Evidence Package format contains no
   provider-specific markup, instructions, or assumptions.
5. **Configuration over code.** Which rules run, in what order, with what
   parameters, is configuration. The Rule Registry reads its configuration at
   startup.
