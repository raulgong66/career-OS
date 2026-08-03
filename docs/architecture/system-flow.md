# CareerOS System Flow

CareerOS has two architectural directions: **acquisition** (knowledge in) and **delivery** (knowledge out).

## End-to-End Flow

```mermaid
flowchart LR
    subgraph Acquisition["Knowledge Acquisition"]
        SourceDoc["External Sources<br/>(DOC / DOCX / PDF / MD)"]
        Framework["Professional Knowledge<br/>Acquisition Framework"]
        HumanReview["Human Review"]
        Profile["Canonical Profile<br/>(profiles/*.yaml)"]
    end

    subgraph Delivery["Knowledge Delivery"]
        ProfileLoader["ProfileLoader"]
        ExportContract["ExportContract<br/>(via ExportContractBuilder)"]
        EvidenceSelector["EvidenceSelector"]
        Generators["Generators<br/>(MarkdownCV / DocxCV / CoverLetter)"]
        Optimizer["CV Optimizer"]
        API["REST API"]
        Frontend["React Frontend"]
        Output["Generated Artifacts<br/>(.md / .docx / tailored CVs)"]
    end

    SourceDoc --> Framework
    Framework --> HumanReview
    HumanReview --> Profile
    Profile --> ProfileLoader
    ProfileLoader --> ExportContract
    ExportContract --> EvidenceSelector
    EvidenceSelector --> Generators
    ProfileLoader --> Optimizer
    Optimizer --> API
    Optimizer --> Frontend
    Generators --> Output
    API --> Output
```

## Acquisition Flow

The acquisition pipeline ingests professional knowledge from external sources and produces validated canonical profile YAML.

```mermaid
flowchart LR
    Source["Source Document<br/>(DOC / DOCX / PDF / MD / ...)"]
    Parser["Parser"]
    ParserOut["ParsedDocument<br/>(text + structure + metadata)"]
    Extractor["Extractor<br/>(LLM + heuristics)"]
    Extraction["ExtractionResult<br/>(entities + confidence + source refs)"]
    Normalizer["Normalizer"]
    Normalized["NormalizedProfile<br/>(schema-ready)"]
    Validator["Validator<br/>(schema + business rules)"]
    Report["ValidationReport"]
    Review["Human Review"]
    Approved["Approved Profile"]
    ProfileFile["Canonical Profile YAML<br/>(profiles/*.yaml)"]

    Source --> Parser
    Parser --> ParserOut
    ParserOut --> Extractor
    Extractor --> Extraction
    Extraction --> Normalizer
    Normalizer --> Normalized
    Normalized --> Validator
    Validator --> Report
    Report --> Review
    Review --> Approved
    Approved --> ProfileFile
```

## Delivery Flow

The delivery pipeline reads canonical profile data and generates audience-specific artifacts.

```mermaid
flowchart LR
    Profile["Profile file<br/>(YAML or JSON)"]
    ProfileLoader["ProfileLoader"]
    ExportContract["ExportContract<br/>(via ExportContractBuilder)"]
    EvidenceSelector["EvidenceSelector"]
    MarkdownCVGenerator["MarkdownCVGenerator"]
    DocxCVGenerator["DocxCVGenerator"]
    CoverLetterGenerator["CoverLetterGenerator"]
    CVOptimizer["CV Optimizer"]
    CLI["CLI"]
    API["REST API<br/>(/generate/*, /optimize-cv, /profiles)"]
    Frontend["React Frontend<br/>(Tailoring Page, Dashboard)"]
    Output["Generated Artifacts"]

    Profile --> ProfileLoader
    ProfileLoader --> ExportContract
    ExportContract --> EvidenceSelector
    EvidenceSelector --> MarkdownCVGenerator
    EvidenceSelector --> DocxCVGenerator
    EvidenceSelector --> CoverLetterGenerator
    ProfileLoader --> CVOptimizer
    MarkdownCVGenerator --> CLI
    MarkdownCVGenerator --> API
    DocxCVGenerator --> API
    CoverLetterGenerator --> API
    CVOptimizer --> API
    CVOptimizer --> Frontend
    API --> Output
```

## Current CLI Flow

```text
Profile -> ProfileLoader -> ExportContract -> EvidenceSelector -> MarkdownCVGenerator -> CLI -> output file
```

## Current API Flow

```text
Profile -> ProfileLoader -> ExportContract -> EvidenceSelector -> MarkdownCVGenerator -> API -> Markdown response
```
