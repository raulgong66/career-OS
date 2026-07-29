# 05 — Data Flow

## Primary Flow: Profile → Reasoning → Generation

```mermaid
flowchart LR
    subgraph Input["Input"]
        ProfileFile["Profile YAML/JSON"]
    end

    subgraph Load["Load"]
        ProfileLoader["ProfileLoader<br/>load(file)"]
        Validator["EntityValidator<br/>validate(profile)"]
    end

    subgraph ReasoningFlow["Reasoning"]
        KG["KnowledgeGraphBuilder<br/>build(profile)"]
        KG_Graph["KnowledgeGraph"]
        Engine["ReasoningEngine<br/>analyze(profile)"]
        Report["ReasoningReport"]
        Findings["ReasoningFindings<br/>from_report(report)"]
        Assembler["EvidencePackageAssembler<br/>assemble(analysis)"]
        Package["EvidencePackage"]
    end

    subgraph Contract["Contract"]
        ExportBuilder["ExportContractBuilder<br/>build(profile, artifact_id, reasoning=findings)"]
        ExportContract["ExportContract<br/>+reasoning: ReasoningFindings"]
        EvidenceSelector["EvidenceSelector<br/>select(contract)"]
    end

    subgraph GenerationFlow["Generation"]
        Registry["GeneratorRegistry<br/>resolve(type, format)"]
        Generator["ArtifactGenerator<br/>generate(contract)"]
    end

    subgraph Output["Output"]
        MD["Markdown CV (.md) + reasoning sections"]
        DOCX["DOCX CV (.docx)"]
        CL["Cover Letter (.md)"]
    end

    ProfileFile --> ProfileLoader
    ProfileLoader --> Validator
    Validator --> KG
    KG --> KG_Graph
    KG_Graph --> Engine
    Engine --> Report
    Report --> Findings
    Findings --> ExportBuilder
    Validator --> ExportBuilder
    ExportBuilder --> ExportContract
    ExportContract --> EvidenceSelector
    EvidenceSelector --> Registry
    Registry --> Generator
    Generator --> MD
    Generator --> DOCX
    Generator --> CL
```

## Acquisition Flow: Source Document → Profile

```mermaid
flowchart LR
    Source["Source DOCX"]
    Reader["DocumentReader<br/>read(path)"]
    Raw["Raw Text"]
    Extractor["TextExtractor<br/>extract(text)"]
    Clean["Cleaned Text"]
    LLM["LLMExtractor<br/>extract(text)"]
    Extracted["ExtractionResult"]
    Builder["CanonicalProfileBuilder<br/>normalize + build"]
    Built["Profile dict"]
    AcqValidator["EntityValidator<br/>validate(profile)"]
    YamlWriter["YamlWriter<br/>write(profile)"]
    ProfileFile["profiles/staging/*.yaml"]

    Source --> Reader
    Reader --> Raw
    Raw --> Extractor
    Extractor --> Clean
    Clean --> LLM
    LLM --> Extracted
    Extracted --> Builder
    Builder --> Built
    Built --> AcqValidator
    AcqValidator --> YamlWriter
    YamlWriter --> ProfileFile
```

## Reasoning Internal Data Flow

```mermaid
flowchart TB
    Profile["Profile dict"]

    subgraph GraphBuild["Knowledge Graph Construction"]
        Person["person node"]
        Experiences["experience nodes<br/>(with USES_SKILL edges)"]
        Skills["skill nodes<br/>(with HAS_SKILL edges)"]
        Edu["education nodes"]
        Orgs["organization nodes<br/>(with AT_ORGANIZATION edges)"]
    end

    subgraph Execution["Rule Execution"]
        Order["RuleRegistry.execution_order()<br/>(topological sort)"]
        Rules["14 Rules execute in order"]
        Context["RuleContext<br/>(graph + profile + params)"]
        Results["list[ReasoningResult]"]
    end

    subgraph Assembly["Result Assembly"]
        Run["engine.run() wraps in AnalysisModel"]
        Analyze["engine.analyze() wraps in ReasoningReport"]
        Pack["EvidencePackageAssembler<br/>sections findings by type"]
    end

    Profile --> GraphBuild
    GraphBuild --> Context

    Context --> Rules
    Order --> Rules
    Rules --> Results
    Results --> Run
    Run --> Analyze
    Analyze --> Pack
```

## API Request Flows

### Artifact Generation (Reasoning-Aware)

```mermaid
sequenceDiagram
    Client->>+API: POST /generate/artifact
    API->>+ProfileLoader: load profile
    ProfileLoader->>ProfileLoader: validate against schema
    ProfileLoader-->>-API: profile dict
    API->>+ReasoningEngine: analyze(profile)
    ReasoningEngine->>ReasoningEngine: build KnowledgeGraph
    ReasoningEngine->>ReasoningEngine: execute 23 rules in dependency order
    ReasoningEngine-->>-API: ReasoningReport
    API->>+ReasoningFindings: from_report(report)
    ReasoningFindings-->>-API: ReasoningFindings
    API->>+ExportContractBuilder: build(profile, artifact_id, reasoning=findings)
    ExportContractBuilder->>ExportContractBuilder: resolve artifact, contexts, sources
    ExportContractBuilder-->>-API: ExportContract (with .reasoning)
    API->>+EvidenceSelector: select(contract)
    EvidenceSelector-->>-API: filtered contract
    API->>+GeneratorRegistry: resolve(artifact_type, format)
    GeneratorRegistry-->>-API: generator instance
    API->>+Generator: generate(contract)
    Generator->>Generator: render reasoning sections from contract.reasoning
    Generator-->>-API: output (str/bytes) with deterministic insights
    API-->>-Client: response with reasoning-augmented artifact
```

### CV Optimization

```mermaid
sequenceDiagram
    Client->>+API: POST /optimize-cv
    API->>+ProfileLoader: load profile
    ProfileLoader-->>-API: profile dict
    API->>+CVOptimizer: optimize_cv(artifact_id, job_desc?)
    CVOptimizer->>CVOptimizer: find artifact, identify sources
    CVOptimizer->>CVOptimizer: compute relevance scores
    CVOptimizer-->>-API: list[Recommendation]
    API-->>-Client: optimization recommendations
```

## Reasoning–Generation Integration (PA-004)

The pipeline entry point `generate_artifact()` in `careeros/pipelines.py` now runs reasoning exactly once per call:

1. **Profile loaded** via `ProfileLoader`
2. **Reasoning executed** via `ReasoningEngine.analyze(profile)` → `ReasoningReport`
3. **Findings extracted** via `ReasoningFindings.from_report(report)` — a lightweight DTO with only the fields generators need
4. **Contract built** via `ExportContractBuilder.build(..., reasoning=findings)` — attaches findings to `ExportContract.reasoning`
5. **Sources filtered** via `EvidenceSelector.select(contract)` — unchanged, operates on sources only
6. **Generator renders** — checks `contract.reasoning` and includes deterministic insights when present

### ReasoningFindings fields exposed to generators

| Field | Source Finding Type | Description |
|---|---|---|
| `strongest_skills` | `strongest_skills` | Ranked skill names |
| `core_competencies` | `core_competencies` | Core competency names |
| `strongest_experience` | `strongest_experience` | Top experience dict |
| `leadership_indicators` | `leadership_experience` | Leadership evidence dicts |
| `technology_breadth` | `technology_breadth` | Technology area names |
| `domain_expertise` | `domain_experience` | Domain names |
| `career_highlights` | `career_highlights` | Highlight dicts |
| `career_stage` | `career_stage_classification` | Stage label (e.g. "Senior") |

### Backward Compatibility

- If no `ReasoningFindings` is attached, `contract.reasoning` is `None` and generators render identically to previous behavior.
- The `to_dict()` method on `ExportContract` intentionally omits the `reasoning` field to avoid serialization changes.
- All existing tests pass without modification.

## Reasoning Data Types (per-rule)

Each reasoning rule reads from the `KnowledgeGraph` via `RuleContext` and produces `ReasoningResult` instances with typed values:

| Rule | Inputs (graph queries) | Output Value Type |
|---|---|---|
| `TotalYearsExperienceRule` | `experiences()` | `float` (years) |
| `CurrentEmployerRule` | `experiences()`, `organizations()` | `str` (org name) |
| `CurrentRoleRule` | `experiences()` | `str` (title) |
| `LongestTenureRule` | `experiences()`, `organizations()` | `dict` |
| `CareerProgressionRule` | `experiences()`, `organizations()` | `dict` (events + summary) |
| `EmploymentGapRule` | `experiences()` | `list[dict]` (gaps) |
| `CareerStageRule` | `experiences()` | `str` (stage label) |
| `StrongestExperienceRule` | `experiences()`, `skills_used_by()` | `list[dict]` (ranked) |
| `LeadershipExperienceRule` | `experiences()`, `organizations()` | `dict` (leadership info) |
| `CloudExperienceRule` | `skills()` | `dict` (cloud providers) |
| `TechnologyBreadthRule` | `skills()`, `experiences()`, `skills_used_by()` | `dict` (tech stats) |
| `DomainExperienceRule` | `experiences()`, `organizations()`, `skills()` | `dict` (industry mapping) |
| `SeniorResponsibilityRule` | `experiences()`, `organizations()`, `skills()` | `dict` (responsibility areas) |
| `CareerHighlightsRule` | `experiences()`, `organizations()`, `skills()`, `skills_used_by()` | `dict` (highlights) |
