# CareerOS Product Backlog

This document is the initial product backlog for CareerOS. It is intended to be the authoritative planning artifact from which future GitHub Issues and GitHub Project items will be created. The backlog is aligned with the project constitution, AI workflow guidance, the current product vision, the canonical profile model, and the profile schema.

## Architectural Capability: Professional Knowledge Acquisition Framework

The Professional Knowledge Acquisition Framework is the architectural capability responsible for ingesting professional knowledge from external sources and producing validated canonical profile data. It is documented in `docs/architecture/professional-knowledge-acquisition-framework.md`.

This capability spans multiple milestones. The first implementation milestone is the **Profile Builder Agent** (M0 below), which handles DOC, DOCX, PDF, and Markdown source documents.

## Milestone M0 – Professional Knowledge Acquisition (Beta)

### PKAF-001 — Define acquisition pipeline interfaces
- Objective: Establish the abstract interfaces for the acquisition pipeline (parse, extract, normalize, validate, review, generate).
- Description: Define the handler protocol and pipeline stage contracts that all acquisition agents will implement. These interfaces live in the architecture documentation and serve as the contract for implementation.
- Acceptance Criteria:
  - The handler interface is documented.
  - Each pipeline stage has a defined input and output contract.
  - The interfaces support the source types planned for Beta (DOC, DOCX, PDF, Markdown).
  - Extensibility for future sources (LinkedIn, Credly, GitHub) is considered in the interface design.
- Dependencies: ADR-0004
- Priority: P0
- Estimated Complexity: M
- Suggested Primary Owner: Claude Code CLI

### PKAF-002 — Implement Profile Builder Agent (DOC/DOCX source)
- Objective: Implement the first acquisition agent capable of ingesting DOC and DOCX source documents into canonical profile YAML.
- Description: Build the Profile Builder Agent as the first implementation of the Professional Knowledge Acquisition Framework. This agent parses DOC and DOCX files, extracts professional entities (person, experiences, education, certifications, skills, achievements, organizations), normalizes the data, validates against the canonical profile schema, presents for human review, and writes the approved profile to `profiles/`.
- Acceptance Criteria:
  - A DOC source document can be parsed, extracted, normalized, validated, and converted into a canonical profile YAML.
  - A DOCX source document follows the same pipeline.
  - The extracted profile validates against `schemas/profile.schema.json`.
  - The human reviewer can inspect, correct, and approve or reject the extracted profile before any data is written.
  - On approval, the profile is written to `profiles/` with source documents tracked as evidence.
  - The resulting profile is loadable by `ProfileLoader` and usable in the existing delivery pipeline without modification.
- Dependencies: PKAF-001
- Priority: P0
- Estimated Complexity: XL
- Suggested Primary Owner: Claude Code CLI

### PKAF-003 — Implement PDF source handler
- Objective: Extend the Profile Builder Agent to support PDF source documents.
- Description: Add PDF parsing and extraction to the Profile Builder Agent. PDF extraction includes text extraction with layout analysis, section hierarchy reconstruction, and confidence scoring for each extracted field.
- Acceptance Criteria:
  - A PDF source document can be processed through the full acquisition pipeline.
  - Each extracted field includes a confidence indicator.
  - Low-confidence extractions are visually flagged during human review.
  - The output conforms to the canonical profile schema.
- Dependencies: PKAF-002
- Priority: P1
- Estimated Complexity: L
- Suggested Primary Owner: Claude Code CLI

### PKAF-004 — Implement Markdown source handler
- Objective: Extend the Profile Builder Agent to support Markdown source documents.
- Description: Add Markdown parsing and extraction to the Profile Builder Agent. Markdown's explicit structure (headings, lists, code blocks, links) should yield the highest extraction confidence among supported formats.
- Acceptance Criteria:
  - A Markdown source document can be processed through the full acquisition pipeline.
  - Extraction confidence is consistently higher than DOC/DOCX/PDF for equivalently structured content.
  - Code blocks and link references in source Markdown are preserved as evidence references or project artifacts where appropriate.
- Dependencies: PKAF-002
- Priority: P1
- Estimated Complexity: M
- Suggested Primary Owner: ChatGPT

### PKAF-005 — Implement human review interface (CLI)
- Objective: Provide an interactive CLI-based review workflow for the Profile Builder Agent.
- Description: Build a CLI review interface that presents extracted profile data grouped by entity type, with source attribution, confidence indicators, diff view (for existing profiles), and inline editing. The reviewer can approve, reject, or edit-and-approve.
- Acceptance Criteria:
  - Extracted entities are displayed by type with source context.
  - Each field shows its confidence level and original source text.
  - If a profile already exists for the person, a diff view shows proposed changes.
  - The reviewer can edit any field before approval.
  - The reviewer can approve, reject, or edit-and-approve.
  - Approval triggers profile generation; rejection returns to the pipeline with a reason.
- Dependencies: PKAF-002
- Priority: P1
- Estimated Complexity: L
- Suggested Primary Owner: ChatGPT

### PKAF-006 — Implement cross-source reconciliation
- Objective: Support incremental acquisition where new sources are reconciled with existing profile data.
- Description: When acquisition runs for a person who already has canonical profile data, the framework reconciles new data with existing data: matching entities by stable IDs, detecting conflicts, proposing additions, and flagging potentially stale entries.
- Acceptance Criteria:
  - Running acquisition on a second source for the same person reconciles rather than replaces.
  - Conflicts between sources are detected and presented to the human reviewer.
  - New entities are proposed as additions.
  - Entities absent from all active sources are flagged as potentially stale.
- Dependencies: PKAF-002
- Priority: P2
- Estimated Complexity: L
- Suggested Primary Owner: GitHub Copilot

## Milestone M1 – Canonical Profile Foundation

### BACKLOG-001 — Create master profile YAML
- Objective: Establish a canonical, repository-owned master profile file.
- Description: Create a single master profile document in YAML that captures the core CareerOS profile structure and can be validated against the schema.
- Acceptance Criteria:
  - A master profile file exists in the repository.
  - The file validates against the canonical profile schema.
  - The file is documented as the primary source of canonical profile data.
- Dependencies: None
- Priority: P0
- Estimated Complexity: M
- Suggested Primary Owner: Human

### BACKLOG-002 — Create sample profiles
- Objective: Provide representative profile examples for validation and reuse.
- Description: Create a small set of sample profile files that demonstrate valid structure across different contexts and use cases.
- Acceptance Criteria:
  - At least two sample profiles exist.
  - Each sample profile validates successfully.
  - The samples are easy to understand and reuse for testing.
- Dependencies: BACKLOG-001
- Priority: P1
- Estimated Complexity: S
- Suggested Primary Owner: ChatGPT

### BACKLOG-003 — Build validator test suite
- Objective: Ensure schema validation remains reliable as the project grows.
- Description: Add automated tests for the validator covering both valid and invalid profile cases.
- Acceptance Criteria:
  - The validator has a test suite.
  - Valid input passes and invalid input fails with clear errors.
  - The test suite can be run locally.
- Dependencies: BACKLOG-001
- Priority: P0
- Estimated Complexity: M
- Suggested Primary Owner: Claude Code CLI

### BACKLOG-004 — Implement profile loader
- Objective: Support loading profile data from repository files.
- Description: Implement a simple loader for canonical profile documents so other components can read profile content consistently.
- Acceptance Criteria:
  - The loader can read YAML and JSON profile files.
  - The loader returns data in a predictable structure.
  - Loader failures are surfaced with clear messages.
- Dependencies: BACKLOG-001, BACKLOG-003
- Priority: P0
- Estimated Complexity: M
- Suggested Primary Owner: Claude Code CLI

### BACKLOG-005 — Implement profile API
- Objective: Expose profile data through a simple application interface.
- Description: Create a lightweight API layer that allows other tools to request and inspect canonical profile data without directly reading files.
- Acceptance Criteria:
  - The API exposes the canonical profile content in a stable form.
  - The API can be exercised locally.
  - The API returns clear errors for missing or invalid data.
- Dependencies: BACKLOG-004
- Priority: P1
- Estimated Complexity: M
- Suggested Primary Owner: GitHub Copilot

## Milestone M2 – Core Engine

### BACKLOG-006 — Define target contexts and export contract
- Objective: Establish the supported audience contexts for artifact generation.
- Description: Define the target context structure and the expected contract for how profile content will be selected and adapted for generated outputs.
- Acceptance Criteria:
  - A documented set of target contexts exists.
  - The contract is consistent with the canonical profile model.
  - The contract is usable by downstream generators.
- Dependencies: BACKLOG-005
- Priority: P1
- Estimated Complexity: M
- Suggested Primary Owner: Human

### BACKLOG-007 — Create resume generation pipeline
- Objective: Produce a resume from canonical profile data.
- Description: Implement the first artifact generation flow for a resume based on the canonical profile and a target context.
- Acceptance Criteria:
  - A resume can be generated from the canonical profile.
  - The generated artifact reflects the selected target context.
  - The output is traceable to the source profile data.
- Dependencies: BACKLOG-006
- Priority: P1
- Estimated Complexity: L
- Suggested Primary Owner: ChatGPT

### BACKLOG-008 — Create CV generation pipeline
- Objective: Produce a CV from canonical profile data.
- Description: Implement a CV generation flow that uses the canonical profile and target context to produce a structured output.
- Acceptance Criteria:
  - A CV can be generated from the canonical profile.
  - The generated output remains consistent with the schema-driven profile model.
  - The generation path is documented for reuse.
- Dependencies: BACKLOG-006
- Priority: P1
- Estimated Complexity: L
- Suggested Primary Owner: ChatGPT

### BACKLOG-009 — Create LinkedIn generation pipeline
- Objective: Produce a LinkedIn profile draft from canonical profile data.
- Description: Implement a generation flow for LinkedIn-ready profile content based on the canonical profile.
- Acceptance Criteria:
  - A LinkedIn profile draft can be generated.
  - The output reflects a defined target context.
  - The output is clearly separated from canonical data.
- Dependencies: BACKLOG-006
- Priority: P1
- Estimated Complexity: M
- Suggested Primary Owner: ChatGPT

## Milestone M3 – Artifact Generation

### BACKLOG-010 — Create portfolio generation pipeline
- Objective: Generate portfolio content from canonical profile data.
- Description: Implement a structured portfolio-generation flow that can surface projects, evidence, and positioning in a reusable format.
- Acceptance Criteria:
  - A portfolio draft can be generated from the canonical profile.
  - The output is based on canonical data and target context.
  - The output can be reviewed without additional manual transformation.
- Dependencies: BACKLOG-006
- Priority: P1
- Estimated Complexity: L
- Suggested Primary Owner: ChatGPT

### BACKLOG-011 — Create cover letter generation pipeline
- Objective: Generate cover letters from canonical profile data.
- Description: Implement cover letter generation with clear support for role-specific tailoring.
- Acceptance Criteria:
  - A cover letter can be generated from the canonical profile.
  - The output references a defined target context.
  - The generated output remains evidence-based and reviewable.
- Dependencies: BACKLOG-006
- Priority: P1
- Estimated Complexity: M
- Suggested Primary Owner: ChatGPT

### BACKLOG-012 — Implement tailoring engine
- Objective: Adapt generated content to a specific opportunity context.
- Description: Create a component that tailors artifacts using target context and available profile evidence without introducing unsupported claims.
- Acceptance Criteria:
  - The engine can select and emphasize relevant profile content for a given context.
  - Tailoring output is auditable and grounded in canonical data.
  - The engine can be tested with a sample target context.
- Dependencies: BACKLOG-007, BACKLOG-008, BACKLOG-009, BACKLOG-010, BACKLOG-011
- Priority: P1
- Estimated Complexity: L
- Suggested Primary Owner: Claude Code CLI

## Milestone M4 – Intelligence

### BACKLOG-013 — Implement evidence selection engine
- Objective: Select supporting evidence for generated artifacts.
- Description: Implement a lightweight engine that chooses relevant evidence for a profile claim or artifact based on the target context.
- Acceptance Criteria:
  - The engine can rank or select evidence items for a given artifact.
  - The selection process is explainable and reviewable.
  - The engine can operate without introducing unsupported claims.
- Dependencies: BACKLOG-012
- Priority: P1
- Estimated Complexity: L
- Suggested Primary Owner: GitHub Copilot

### BACKLOG-014 — Create documentation site
- Objective: Publish the project guidance and usage flow in a discoverable format.
- Description: Create a simple documentation site that explains how to use CareerOS, the profile model, and the artifact generation workflow.
- Acceptance Criteria:
  - A documentation entry point exists.
  - The docs cover profile structure, validation, and generation workflow.
  - The site can be reviewed locally.
- Dependencies: BACKLOG-007, BACKLOG-008, BACKLOG-009, BACKLOG-010, BACKLOG-011
- Priority: P2
- Estimated Complexity: M
- Suggested Primary Owner: ChatGPT

## Milestone M6 – Professional Knowledge Reasoning

The Professional Knowledge Reasoning Layer sits between the Knowledge Graph
and AI providers. It performs deterministic analysis of the canonical profile
and produces a structured Evidence Package that every AI provider consumes.
Architecture is documented in `docs/adr/0005-professional-knowledge-reasoning-layer.md`,
`docs/architecture/professional-knowledge-reasoning.md`, and related documents.

### PKR-001 — Implement Rule interface and Rule Registry
- Objective: Establish the abstract interface for deterministic reasoning rules.
- Description: Define the Rule abstract base class with `name`, `description`, `input_types`, and `evaluate(graph) -> list[Finding]`. Implement the Rule Registry that discovers, validates, and orders registered rules.
- Acceptance Criteria:
  - The Rule interface is defined and documented.
  - The Rule Registry can register, retrieve, and iterate rules.
  - Rules declare their input node types.
  - The registry rejects duplicate rule names.
  - The registry provides deterministic ordering for execution.
- Dependencies: M5 (Knowledge Graph), ADR-0005
- Priority: P0
- Estimated Complexity: M
- Suggested Primary Owner: Claude Code CLI

### PKR-002 — Implement Evidence Package data model
- Objective: Create the structured data model for the Evidence Package.
- Description: Implement the Evidence Package schema as Python dataclasses. Include all sections: CandidateSummary, RelevantExperience, MatchingSkill, Education, Strength, Weakness, MissingCompetency, SupportingEvidence, Recommendation. The model is versioned and serializable.
- Acceptance Criteria:
  - All Evidence Package sections are implemented as dataclasses.
  - The model can be serialized to and from YAML/JSON.
  - The model validates required fields on construction.
  - Version metadata is included in every package.
  - The model is independent of any AI provider.
- Dependencies: PKR-001
- Priority: P0
- Estimated Complexity: M
- Suggested Primary Owner: Claude Code CLI

### PKR-003 — Implement Finding and Evidence Set models
- Objective: Create the intermediate data structures for the analysis pipeline.
- Description: Implement Finding (rule name, value, evidence node references, confidence) and Evidence Set (theme, findings list, aggregate confidence). These are consumed by the Evidence Package Assembler.
- Acceptance Criteria:
  - Finding stores rule name, typed value, graph node references, and confidence.
  - Evidence Set groups related findings by theme.
  - Confidence is computed from evidence quantity and recency heuristics.
  - Both models are immutable and hashable.
- Dependencies: PKR-001
- Priority: P1
- Estimated Complexity: S
- Suggested Primary Owner: Claude Code CLI

### PKR-004 — Implement Knowledge Graph query utilities
- Objective: Provide reusable query helpers that rules use to traverse the graph.
- Description: Implement query functions that rules call to find nodes by type, traverse edges by type, compute date ranges, and resolve aliases. These are not rules themselves but shared utilities for rule implementation.
- Acceptance Criteria:
  - Query functions exist for finding nodes by type, label, and property.
  - Edge traversal by type (outgoing and incoming) is supported.
  - Date range computation (duration, overlap, recency) is implemented.
  - All functions accept a KnowledgeGraph and return typed results.
- Dependencies: M5 (Knowledge Graph)
- Priority: P0
- Estimated Complexity: M
- Suggested Primary Owner: Claude Code CLI

### PKR-005 — Implement tenure rules
- Objective: Implement deterministic tenure computation rules.
- Description: Implement the Tenure rule group: total_years_of_experience, years_per_organization, years_of_experience_per_skill, average_tenure_per_role, recurring_organizations.
- Acceptance Criteria:
  - Total years is computed from all experience date ranges, deduplicating overlap.
  - Per-organization tenure sums durations across AT_ORGANIZATION edges.
  - Per-skill tenure sums durations across USES_SKILL edges.
  - Recurring organizations are detected and flagged.
  - Current experiences contribute up to the analysis date.
- Dependencies: PKR-004
- Priority: P1
- Estimated Complexity: M
- Suggested Primary Owner: Claude Code CLI

### PKR-006 — Implement experience rules
- Objective: Implement deterministic experience analysis rules.
- Description: Implement the Experience rule group: strongest_experience, recent_experience, career_progression, leadership_evidence, management_evidence.
- Acceptance Criteria:
  - Strongest experience is determined by title hierarchy and scope.
  - Most recent experience is identified by end date or isCurrent flag.
  - Career progression pattern (upward, lateral, varied) is classified.
  - Leadership evidence is detected from titles and scope text.
  - Management evidence is a stricter subset of leadership evidence.
- Dependencies: PKR-004
- Priority: P1
- Estimated Complexity: M
- Suggested Primary Owner: Claude Code CLI

### PKR-007 — Implement skill rules
- Objective: Implement deterministic skill analysis rules.
- Description: Implement the Skills rule group: most_used_technology, skill_recency, years_of_experience_per_skill, programming_language_evidence, infrastructure_evidence, security_evidence, cloud_expertise.
- Acceptance Criteria:
  - Most-used technology is identified by USES_SKILL edge count.
  - Skill recency is determined from the most recent USED_IN_EXPERIENCE date.
  - Programming languages, infrastructure tools, security skills, and cloud platforms are grouped and reported separately.
  - Each skill finding includes years of experience, recency, and evidence count.
- Dependencies: PKR-004
- Priority: P1
- Estimated Complexity: M
- Suggested Primary Owner: Claude Code CLI

### PKR-008 — Implement education rules
- Objective: Implement deterministic education analysis rules.
- Description: Implement the Education rule group: highest_education, education_relevance.
- Acceptance Criteria:
  - Highest education degree is identified by degree level hierarchy.
  - Education relevance to current career is scored by field-of-study alignment.
  - Multiple degrees at the same level resolve by recency.
- Dependencies: PKR-004
- Priority: P2
- Estimated Complexity: S
- Suggested Primary Owner: Claude Code CLI

### PKR-009 — Implement Evidence Package Assembler
- Objective: Combine all rule findings into the final Evidence Package.
- Description: Implement the EvidencePackageAssembler that collects Findings from all rules, groups them into Evidence Sets, computes aggregate confidence, and produces the EvidencePackage.
- Acceptance Criteria:
  - All Findings from all registered rules are included in the package.
  - Findings are grouped into Evidence Sets by theme.
  - The candidate summary section is built from aggregate findings.
  - Strengths and weaknesses are derived from positive and negative findings.
  - The package is serializable for AI provider consumption.
- Dependencies: PKR-002, PKR-003, PKR-005, PKR-006, PKR-007, PKR-008
- Priority: P0
- Estimated Complexity: M
- Suggested Primary Owner: Claude Code CLI

### PKR-010 — Implement gap analysis foundation
- Objective: Enable comparison of profile capabilities against requirements.
- Description: Implement the GapDetector that compares Evidence Package findings against a target context (job description, role requirements). Produces Gap records with severity scoring.
- Acceptance Criteria:
  - Requirements can be provided as a structured requirement set.
  - Gaps are detected for missing skills, insufficient experience, and absent certifications.
  - Gap severity is scored (critical, major, minor).
  - Gaps include references to the relevant rule findings.
- Dependencies: PKR-009
- Priority: P2
- Estimated Complexity: L
- Suggested Primary Owner: Claude Code CLI

### PKR-011 — Write rule unit tests
- Objective: Ensure all rules are thoroughly tested.
- Description: Write comprehensive unit tests for every rule in the Tenure, Experience, Skills, and Education rule groups. Test edge cases: empty graphs, missing properties, overlapping dates, duplicate entries, and boundary conditions.
- Acceptance Criteria:
  - Every rule has at minimum one happy-path test and one edge-case test.
  - Edge cases cover empty experience lists, missing dates, single-experience profiles, and maximum-date-range profiles.
  - All tests are deterministic and do not require AI.
  - Test coverage exceeds 90% for rule code.
- Dependencies: PKR-005, PKR-006, PKR-007, PKR-008
- Priority: P1
- Estimated Complexity: L
- Suggested Primary Owner: Claude Code CLI

### PKR-012 — Integrate reasoning layer with artifact pipeline
- Objective: Wire the reasoning layer into the existing artifact generation flow.
- Description: Modify the artifact generation pipeline (CV, cover letter, etc.) to consume the Evidence Package instead of the raw canonical profile. AI providers receive the Evidence Package as their input.
- Acceptance Criteria:
  - Existing artifact generators accept the Evidence Package as their input.
  - The reasoning layer runs automatically before artifact generation.
  - The Evidence Package is cached per profile version.
  - Generator prompts are updated to reference evidence fields instead of profile fields.
  - All existing artifact tests pass with the new input contract.
- Dependencies: PKR-009, BACKLOG-007, BACKLOG-011
- Priority: P1
- Estimated Complexity: L
- Suggested Primary Owner: Claude Code CLI

## Milestone M5 – Quality & Release

### BACKLOG-015 — Add CI validation for schema and outputs
- Objective: Ensure repository quality with automated checks.
- Description: Add continuous validation for schema compliance, profile integrity, and generated artifact quality.
- Acceptance Criteria:
  - CI validates schema and profile structure automatically.
  - Invalid changes fail the workflow clearly.
  - The validation path is documented for contributors.
- Dependencies: BACKLOG-005, BACKLOG-006
- Priority: P0
- Estimated Complexity: M
- Suggested Primary Owner: Claude Code CLI

### BACKLOG-016 — Prepare release packaging and onboarding
- Objective: Make CareerOS easy to adopt and release.
- Description: Prepare a release-ready structure with onboarding notes, setup instructions, and a clear packaging flow for contributors and users.
- Acceptance Criteria:
  - A release checklist exists.
  - Installation and usage instructions are available.
  - The initial release package is understandable to a new contributor.
- Dependencies: BACKLOG-014, BACKLOG-015
- Priority: P1
- Estimated Complexity: S
- Suggested Primary Owner: Human
