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

    subgraph Contract["Contract"]
        ExportBuilder["ExportContractBuilder<br/>build(profile, artifact_id)"]
        ExportContract["ExportContract"]
        EvidenceSelector["EvidenceSelector<br/>select(contract)"]
    end

    subgraph ReasoningFlow["Reasoning"]
        KG["KnowledgeGraphBuilder<br/>build(profile)"]
        KG_Graph["KnowledgeGraph"]
        Engine["ReasoningEngine<br/>analyze(profile)"]
        Report["ReasoningReport"]
        Assembler["EvidencePackageAssembler<br/>assemble(analysis)"]
        Package["EvidencePackage"]
    end

    subgraph GenerationFlow["Generation"]
        Registry["GeneratorRegistry<br/>resolve(type, format)"]
        Generator["ArtifactGenerator<br/>generate(contract)"]
    end

    subgraph Output["Output"]
        MD["Markdown CV (.md)"]
        DOCX["DOCX CV (.docx)"]
        CL["Cover Letter (.md)"]
    end

    ProfileFile --> ProfileLoader
    ProfileLoader --> Validator
    Validator --> ExportBuilder
    ExportBuilder --> ExportContract
    ExportContract --> EvidenceSelector
    EvidenceSelector --> Registry
    Registry --> Generator
    Generator --> MD
    Generator --> DOCX
    Generator --> CL

    ProfileLoader -.-> KG
    KG --> KG_Graph
    KG_Graph --> Engine
    Engine --> Report
    Report --> Assembler
    Assembler --> Package
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

### Artifact Generation

```mermaid
sequenceDiagram
    Client->>+API: POST /generate/artifact
    API->>+ProfileLoader: load profile
    ProfileLoader->>ProfileLoader: validate against schema
    ProfileLoader-->>-API: profile dict
    API->>+ExportContractBuilder: build(profile, artifact_id)
    ExportContractBuilder->>ExportContractBuilder: resolve artifact, contexts, sources
    ExportContractBuilder-->>-API: ExportContract
    API->>+EvidenceSelector: select(contract)
    EvidenceSelector-->>-API: filtered contract
    API->>+GeneratorRegistry: resolve(artifact_type, format)
    GeneratorRegistry-->>-API: generator instance
    API->>+Generator: generate(contract)
    Generator-->>-API: output (str/bytes)
    API-->>-Client: response with generated artifact
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
