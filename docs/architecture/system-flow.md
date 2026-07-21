# CareerOS System Flow

This diagram reflects the current implemented Markdown CV generation flow.

```mermaid
flowchart LR
    Profile["Profile file<br/>(YAML or JSON)"]
    ProfileLoader["ProfileLoader"]
    ExportContract["ExportContract<br/>(via ExportContractBuilder)"]
    EvidenceSelector["EvidenceSelector"]
    MarkdownCVGenerator["MarkdownCVGenerator"]
    CLI["CLI<br/>generate-markdown-cv"]
    API["API<br/>POST /generate/markdown-cv"]
    Output["Markdown output file"]
    Response["Markdown response"]

    CLI --> Profile
    API --> Profile
    Profile --> ProfileLoader
    ProfileLoader --> ExportContract
    ExportContract --> EvidenceSelector
    EvidenceSelector --> MarkdownCVGenerator
    MarkdownCVGenerator --> CLI
    MarkdownCVGenerator --> API
    CLI --> Output
    API --> Response
```

Current CLI flow:

```text
Profile -> ProfileLoader -> ExportContract -> EvidenceSelector -> MarkdownCVGenerator -> CLI -> output file
```

Current API flow:

```text
Profile -> ProfileLoader -> ExportContract -> EvidenceSelector -> MarkdownCVGenerator -> API -> Markdown response
```
