# CSKS Knowledge Model

**Version**: 1.0
**Milestone**: M1.22
**Status**: Draft (normative for M1.22 implementation)

---

## 1. Entity Definitions

All entities are frozen dataclasses with a stable `id` (UUID or deterministic hash of source path + entity type). Entities are immutable after construction.

### 1.1 Domain

```python
@dataclass(frozen=True)
class Domain:
    id: str                          # e.g., "domain-profile-management"
    name: str                        # "Profile Management"
    description: str                 # "Load, validate, and persist canonical profiles"
    owner_domain: str                # "core" (self)
    source_path: str                 # "docs/architecture/02-domain-map.md"
    components: list[str]            # component ids contained
    dependencies: list[str]          # domain ids this domain depends on
    status: Literal["implemented", "planned", "deprecated"]
    tags: list[str]                  # ["core", "foundational"]
```

### 1.2 ArchitectureComponent

```python
@dataclass(frozen=True)
class ArchitectureComponent:
    id: str                          # "component-profile-loader"
    name: str                        # "ProfileLoader"
    component_type: Literal["class", "function", "module", "protocol", "factory"]
    domain_id: str                   # "domain-profile-management"
    source_path: str                 # "careeros/profile_loader.py"
    line_start: int                  # 1
    line_end: int                    # 150
    public_api: list[str]            # ["load", "validate"]
    dependencies: list[str]          # component ids this depends on
    status: Literal["implemented", "planned", "deprecated"]
    tags: list[str]
```

### 1.3 APIEndpoint

```python
@dataclass(frozen=True)
class APIEndpoint:
    id: str                          # "api-get-profiles"
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"]
    path: str                        # "/profiles"
    summary: str                     # "List all profiles"
    request_model: str | None        # "ProfileListRequest"
    response_model: str              # "list[ProfileInfo]"
    path_params: list[str]           # []
    query_params: list[str]          # []
    status: Literal["stable", "deprecated", "legacy"]
    source_path: str                 # "api/main.py"
    line_start: int
    line_end: int
    tags: list[str]                  # ["profiles", "read"]
```

### 1.4 CLICommand

```python
@dataclass(frozen=True)
class CLICommand:
    id: str                          # "cli-generate-markdown-cv"
    name: str                        # "generate-markdown-cv"
    description: str                 # "Generate Markdown CV"
    arguments: list[dict]            # [{"name": "profile_file", "required": true}]
    options: list[dict]              # [{"name": "--output", "type": "str"}]
    source_path: str                 # "careeros_cli/main.py"
    line_start: int
    line_end: int
    tags: list[str]                  # ["generation", "cv"]
```

### 1.5 Rule

```python
@dataclass(frozen=True)
class Rule:
    id: str                          # "rule-total-years-experience"
    name: str                        # "TotalYearsExperienceRule"
    description: str                 # "Computes total years of experience"
    rule_type: Literal["tenure", "experience", "skill", "education", "recommendation"]
    inputs: list[dict]               # [{"type": "experiences", "query": "experiences()"}]
    output_type: str                 # "float"
    output_description: str          # "Total years of professional experience"
    confidence: float                # 1.0 (deterministic)
    dependencies: list[str]          # rule ids this depends on
    source_path: str                 # "careeros/reasoning/rules/tenure_rules.py"
    line_start: int
    line_end: int
    tags: list[str]                  # ["tenure", "core"]
```

### 1.6 Generator

```python
@dataclass(frozen=True)
class Generator:
    id: str                          # "generator-markdown-cv"
    name: str                        # "MarkdownCVGenerator"
    artifact_types: list[str]        # ["CV"]
    output_formats: list[str]        # ["markdown"]
    source_path: str                 # "careeros/generators/markdown_cv.py"
    line_start: int
    line_end: int
    consumes_contract_fields: list[str]  # ["profile", "artifact_id", "reasoning"]
    produces: list[str]              # ["markdown_cv"]
    tags: list[str]
```

### 1.7 Schema

```python
@dataclass(frozen=True)
class Schema:
    id: str                          # "schema-skill"
    name: str                        # "skill"
    title: str                       # "Skill"
    description: str                 # "Professional skill with proficiency"
    fields: list[dict]               # [{"name": "name", "type": "string", "required": true}]
    required: list[str]              # ["name", "id"]
    enums: list[str]                 # []
    source_path: str                 # "schemas/skill.schema.json"
    version: str                     # "1.0.0"
    tags: list[str]
```

### 1.8 Test

```python
@dataclass(frozen=True)
class Test:
    id: str                          # "test-total-years-experience"
    name: str                        # "test_total_years_experience"
    test_type: Literal["unit", "integration", "e2e"]
    target_component_ids: list[str]  # ["rule-total-years-experience"]
    source_path: str                 # "tests/test_tenure_rules.py"
    line_start: int
    line_end: int
    tags: list[str]
```

### 1.9 ADR

```python
@dataclass(frozen=True)
class ADR:
    id: str                          # "adr-004"
    number: int                      # 4
    title: str                       # "Core Platform Boundaries"
    status: Literal["proposed", "accepted", "superseded", "rejected"]
    summary: str                     # "Establishes Core/Module/App boundary..."
    decision: str                    # "Establish explicit Core/Module/App boundary..."
    consequences: dict               # {"positive": [...], "negative": [...]}
    source_path: str                 # "docs/adr/0004-core-platform-boundaries.md"
    tags: list[str]                  # ["architecture", "boundaries"]
```

### 1.10 Milestone

```python
@dataclass(frozen=True)
class Milestone:
    id: str                          # "m1.21-artifact-workspace"
    number: str                      # "M1.21"
    title: str                       # "Artifact Workspace Vertical Slice"
    status: Literal["planned", "in_progress", "completed", "blocked"]
    merge_commit: str | None         # "a581acd47fce843c087ae02dc4d91c3bb6d5c75d"
    checkpoint_tag: str | None       # "m1.21-artifact-workspace"
    spec_path: str                   # "docs/platform-beta/M1.21-Artifact-Workspace-Vertical-Slice.md"
    acceptance_criteria: list[str]   # ["Resume Generation card opens...", "..."]
    verification_results: dict       # {"backend_tests": "733 passed", "..."}
    source_path: str                 # "docs/platform-beta/M1.21-Artifact-Workspace-Vertical-Slice.md"
    tags: list[str]
```

### 1.11 Configuration

```python
@dataclass(frozen=True)
class Configuration:
    id: str                          # "config-pyproject-dependencies"
    file_path: str                   # "pyproject.toml"
    section: str                     # "dependencies"
    key: str                         # "httpx"
    value: str                       # "^0.27.0"
    description: str                 # "HTTP client for AI provider calls"
    tags: list[str]
```

### 1.12 Principle

```python
@dataclass(frozen=True)
class Principle:
    id: str                          # "principle-knowledge-before-documents"
    source: Literal["manifesto", "architecture_guardrail"]
    number: int | None               # 3 (manifesto section)
    title: str                       # "Knowledge Before Documents"
    statement: str                   # "The resume is not the source of truth..."
    implications: list[str]          # ["One fact stored once", "Change propagates", "..."]
    rejects: list[str]               # ["features that fragment knowledge", "..."]
    source_path: str                 # "docs/MANIFESTO.md"
    tags: list[str]
```

### 1.13 DataFlow

```python
@dataclass(frozen=True)
class DataFlow:
    id: str                          # "flow-artifact-generation"
    name: str                        # "Primary: Profile → Reasoning → Generation"
    steps: list[dict]                # [{"step": 1, "component": "ProfileLoader", "input": "ProfileFile", "output": "ProfileDict"}]
    source_path: str                 # "docs/architecture/05-data-flow.md"
    tags: list[str]
```

### 1.14 Dependency

```python
@dataclass(frozen=True)
class Dependency:
    id: str                          # "dep-reasoning-on-knowledge"
    from_id: str                     # "domain-reasoning"
    to_id: str                       # "domain-knowledge"
    dep_type: Literal["runtime", "import", "data", "architectural"]
    description: str                 # "ReasoningEngine depends on KnowledgeGraphBuilder at runtime"
    source_path: str                 # "docs/architecture/03-module-dependencies.md"
    tags: list[str]
```

---

## 2. Relationship Definitions

All relationships are directed edges in the Knowledge Graph.

| Relationship | From Type(s) | To Type(s) | Inverse | Description |
|---|---|---|---|---|
| `contains` | Domain → ArchitectureComponent | contains | Domain owns component |
| `depends_on` | ArchitectureComponent → ArchitectureComponent | depends_on | Runtime/import dependency |
| `depends_on` | Domain → Domain | depends_on | Domain-level dependency |
| `produces` | ArchitectureComponent → Schema/Generator/APIEndpoint | consumes | Component generates artifact |
| `consumes` | ArchitectureComponent → Schema/Generator/APIEndpoint | produces | Component uses artifact |
| `implements` | Rule → FindingType | implemented_by | Rule produces finding |
| `validates_against` | Domain/Component → Schema | validated_by | Profile conforms to schema |
| `flows_to` | DataFlowStep → DataFlowStep | flows_from | Sequential pipeline step |
| `references` | ADR → Component/Decision | referenced_by | ADR governs component |
| `specifies` | Milestone → Deliverable | specified_by | Spec defines deliverable |
| `tags` | Test → Component | tagged_by | Test exercises component |
| `configures` | Configuration → Component | configured_by | Config controls component |
| `has_finding` | Rule → FindingType | finding_of | Rule produces finding type |
| `has_step` | DataFlow → DataFlowStep | step_of | DataFlow contains step |

---

## 3. Finding Types (from Reasoning Engine)

| Finding Type | Source Rule(s) | Description |
|---|---|---|
| `total_years_experience` | TotalYearsExperienceRule | Total professional years |
| `current_employer` | CurrentEmployerRule | Current organization name |
| `current_role` | CurrentRoleRule | Current job title |
| `longest_tenure` | LongestTenureRule | Longest single tenure |
| `career_progression` | CareerProgressionRule | Career trajectory events |
| `employment_gaps` | EmploymentGapRule | Gaps between roles |
| `career_stage` | CareerStageRule | Junior/Mid/Senior/Principal |
| `strongest_experience` | StrongestExperienceRule | Ranked experiences |
| `leadership_experience` | LeadershipExperienceRule | Leadership evidence |
| `cloud_experience` | CloudExperienceRule | Cloud provider exposure |
| `technology_breadth` | TechnologyBreadthRule | Tech area statistics |
| `domain_experience` | DomainExperienceRule | Industry mapping |
| `senior_responsibility` | SeniorResponsibilityRule | Responsibility areas |
| `career_highlights` | CareerHighlightsRule | Top achievements |
| `strongest_skills` | StrongestSkillsRule | Top skills by usage |
| `core_competencies` | CoreCompetenciesRule | Core competency names |

---

## 4. Query Patterns (Normative)

The Query Engine MUST support these patterns:

### 4.1 Entity Lookup
```text
Input:  "What is the TotalYearsExperienceRule?"
Output: Rule entity with inputs, outputs, source path
```

### 4.2 Type Filter
```text
Input:  "List all domains"
Output: [Domain, Domain, ...] (8 domains)
```

### 4.3 Dependency Traversal
```text
Input:  "What depends on Profile Management?"
Output: [Domain, Domain, ...] with dependency paths
```

### 4.4 Data Flow Path
```text
Input:  "Data flow for artifact generation"
Output: [DataFlowStep, DataFlowStep, ...] (6 steps)
```

### 4.5 Capability Query
```text
Input:  "Does CareerOS support PDF generation?"
Output: "No — only Markdown and DOCX implemented" + citation to capabilities table
```

### 4.5 Status Query
```text
Input:  "M1.21 status"
Output: "Completed (checkpoint tag: m1.21-artifact-workspace, merge: a581acd)"
```

### 4.6 Impact Analysis
```text
Input:  "What breaks if I change ProfileLoader?"
Output: [Component, Component, ...] with dependency paths
```

---

## 5. Answer Format (Normative)

Every query returns:

```python
@dataclass(frozen=True)
class CSKSAnswer:
    answer: str                           # Human-readable answer
    citations: list[Citation]             # Source references
    confidence: float                     # 1.0 for deterministic
    entities_found: int                   # Count of entities examined
    query_time_ms: int                    # Performance metric
    query_type: str                       # "lookup", "traversal", "filter", "path", "status", "impact"

@dataclass(frozen=True)
class Citation:
    file: str                             # Relative path from repo root
    line_start: int
    line_end: int
    text: str                             # Relevant snippet
    entity_id: str                        # Referenced entity id
```

---

## 6. Extraction Rules (Normative)

### 6.1 Python Source (AST)
- Classes → ArchitectureComponent (type="class")
- Functions → ArchitectureComponent (type="function")
- Imports → depends_on edges
- Class inheritance → depends_on
- Decorators (e.g., `@app.get`) → APIEndpoint

### 6.2 TypeScript/React (AST)
- Components → ArchitectureComponent
- Hooks, services → ArchitectureComponent
- Route definitions → APIEndpoint (frontend routes)

### 6.3 Markdown (AST)
- Headings → section structure
- ADR frontmatter → ADR entity
- Tables → structured data extraction
- Mermaid diagrams → Dependency/DataFlow edges

### 6.4 JSON Schema
- Each `.schema.json` → Schema entity
- Properties → Schema.fields
- Required → Schema.required
- Enum → Schema.enums

### 6.5 YAML/TOML Config
- Key-value pairs → Configuration entities
- Nested sections preserved

### 6.6 Git
- Tags → Milestone.checkpoint_tag
- Commit messages → merge_commit for Milestone

---

## 7. Confidence Model

| Confidence | Meaning |
|---|---|
| 1.0 | Deterministic extraction from structured source (code, schema, config) |
| 0.9 | Structured documentation (ADR, spec, architecture doc with frontmatter) |
| 0.8 | Semi-structured docs (architecture docs with clear sections) |
| 0.7 | Prose documentation (requires NLP, not in M1.22) |
| <0.7 | Not extracted in M1.22 |

**M1.22 only extracts confidence ≥0.8 sources.**

---

## 8. Index Schema (File-Based)

The incremental index is stored as:

```
.csks-index/
├── entities/
│   ├── domain-*.json
│   ├── component-*.json
│   ├── api-endpoint-*.json
│   ├── cli-command-*.json
│   ├── rule-*.json
│   ├── generator-*.json
│   ├── schema-*.json
│   ├── test-*.json
│   ├── adr-*.json
│   ├── milestone-*.json
│   ├── configuration-*.json
│   ├── principle-*.json
│   ├── dataflow-*.json
│   └── dependency-*.json
├── edges/
│   ├── contains.jsonl
│   ├── depends_on.jsonl
│   ├── produces.jsonl
│   ├── flows_to.jsonl
│   └── ...
├── metadata.json           # {version, last_indexed, entity_counts, git_commit}
└── git_state.json          # {indexed_commit, indexed_files_hashes}
```

---

## 8. Versioning

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-08-02 | Initial release for M1.22 |
| 1.1 | 2026-08-03 | Document implemented entity-type registry (M1.22) |

---

## Appendix A: Implemented Entity Type Registry (M1.22)

M1.22 stores CSKS entities as `GraphNode`/`GraphEdge` instances in the existing
`careeros.knowledge.KnowledgeGraph` (see ADR-008). The implemented registry
includes the normative types above plus the extraction-oriented types below:

| Entity Type | Source | ID Pattern | Example |
|---|---|---|---|
| `domain` | `docs/architecture/02-domain-map.md`, `09-core-vs-modules.md` | `domain.{slug}` | `domain.profile_management` |
| `component` | Python classes/functions | `component.{module}.{name}` | `component.careeros.profile_loader.ProfileLoader` |
| `rule` | Classes named `*Rule` | `rule.{snake_case}` | `rule.total_years_experience` |
| `generator` | Classes named `*Generator` | `generator.{snake_case}` | `generator.markdown` |
| `api_endpoint` | `@app.<method>` decorators | `api.{method}.{path}` | `api.get.profiles` |
| `cli_command` | `@app.command` decorators | `cli.{name}` | `cli.version` |
| `test` | `tests/` functions named `test_*` | `test.{module}.{name}` | `test.tests.test_sample.test_sample` |
| `dependency` | Python imports | `dependency.{module}.{import}.{name}` | `dependency.careeros.services.careeros.profile_loader.ProfileLoader` |
| `adr` | `# ADR 0000:` headings or frontmatter | `adr.{number:03d}` | `adr.008` |
| `milestone` | Git milestone tags | `milestone.{tag}` | `milestone.m1.21-artifact-workspace` |
| `schema` | `*.schema.json` | `schema.{name}` | `schema.skill` |
| `configuration` | TOML/YAML/.env files | `configuration.{file}.{key}` | `configuration.pyproject.project` |
| `document` | Markdown headings | `document.{stem}.{heading}` | `document.02_domain_map.domain_map` |
| `mermaid_edge` | Mermaid diagram edges | `mermaid.{stem}.{from}--{to}` | `mermaid.02_domain_map.Profile--Schema` |
| `table_row` | Markdown tables | `table_row.{stem}.{line}_{row}` | `table_row.02_domain_map.18_2` |
| `release` | Git release tags | `release.{tag}` | `release.v1.0.0` |
| `tag` | Other Git tags | `tag.{tag}` | `tag.some-tag` |

`principle` and `dataflow` are defined in the normative catalog but are not
extracted in M1.22; `dataflow` answers use the deterministic query-engine
patterns in section 4.3, and `principle` extraction is planned for a later
milestone.

---

*This knowledge model is normative for M1.22 implementation. All extractors, builders, and query engines MUST conform to these definitions.*