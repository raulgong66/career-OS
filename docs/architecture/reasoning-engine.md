# Reasoning Engine

## Overview

The Reasoning Engine is the deterministic core of the Professional Knowledge
Reasoning Layer. It accepts a Knowledge Graph, executes registered rules in
dependency order, collects findings, and produces a structured Analysis Model.
The Evidence Package Assembler then converts the Analysis Model into the
Evidence Package consumed by AI providers.

## Architecture Flow

```
KnowledgeGraph
      │
      ▼
  ReasoningEngine
      │
      ├── RuleRegistry (dependency-sorted)
      │       ├── Rule A
      │       ├── Rule B  (depends on A)
      │       └── Rule C  (depends on B)
      │
      ├── RuleContext (graph + profile + parameters)
      │
      ├── For each rule in execution order:
      │       rule.execute(context) → list[ReasoningResult]
      │
      └── AnalysisModel
              │
              ▼
      EvidencePackageAssembler
              │
              ▼
      EvidencePackage
```

## Package Structure

```
careeros/reasoning/
├── __init__.py       # Public API exports
├── models.py         # ReasoningResult, Evidence, EvidenceSet,
│                     # EvidencePackage, RuleContext, AnalysisModel
├── rule.py           # Rule ABC (abstract base class)
├── registry.py       # RuleRegistry (register, unregister, validate,
│                     # topological sort, cycle detection)
├── engine.py         # ReasoningEngine (graph → analysis)
└── assembler.py      # EvidencePackageAssembler (analysis → package)
```

## Data Models

### ReasoningResult

A single finding produced by a Rule execution.

```
- rule_id: str          — which rule produced this
- finding_type: str     — semantic category (e.g. "skill_recency")
- value: Any            — the finding value
- confidence: float     — 0.0–1.0
- evidence_refs: tuple[str] — graph node/edge IDs
- metadata: dict        — additional context
```

### Evidence

A reference to a supporting data point.

```
- id: str
- type: str
- source: str
- summary: str
- references: dict
```

### EvidenceSet

A themed grouping of Evidence and Findings.

```
- theme: str
- evidence: tuple[Evidence]
- findings: tuple[ReasoningResult]
```

### RuleContext

The execution environment passed to every Rule.

```
- graph: KnowledgeGraph      — the immutable graph
- profile: dict              — raw canonical profile
- parameters: dict           — configurable parameters
```

### AnalysisModel

The complete output of one Reasoning Engine execution.

```
- profile_id: str
- generated_at: datetime
- reasoning_results: tuple[ReasoningResult]
- evidence: tuple[Evidence]
- evidence_sets: tuple[EvidenceSet]
- execution_stats: dict
```

### EvidencePackage

The output contract for AI providers. Detailed in `evidence-package.md`.

```
- meta, candidate_summary, relevant_experiences,
  matching_skills, education, strengths, weaknesses,
  missing_competencies, supporting_evidence, recommendations,
  rule_summary
```

## Rule Interface

```python
class Rule(ABC):
    @property
    def id(self) -> str: ...
    @property
    def name(self) -> str: ...
    @property
    def description(self) -> str: ...
    @property
    def dependencies(self) -> list[str]: ...   # default []

    def execute(self, context: RuleContext) -> list[ReasoningResult]: ...
```

Rules are pure functions. They accept a RuleContext and return a list of
ReasoningResults. They have no side effects, no state, and no AI dependency.

## RuleRegistry

Capabilities:
- `register(rule)` — add a rule; rejects duplicates with `DuplicateRuleError`
- `unregister(rule_id)` — remove a rule; no-op if absent
- `get(rule_id)` — retrieve a rule by ID
- `list()` — return all registered rules
- `validate_dependencies()` — verify all dependency references exist; raises
  `MissingDependencyError` for unresolvable references
- `execution_order()` — return rules sorted topologically using Kahn's
  algorithm; raises `CircularDependencyError` when cycles are detected

## ReasoningEngine

```
engine = ReasoningEngine(registry)
analysis = engine.run(graph, profile, parameters)
```

The engine:

1. Creates a `RuleContext` from the graph, profile, and parameters.
2. Calls `registry.execution_order()` for sorted rule list.
3. Iterates rules in order, calling `rule.execute(context)`.
4. Collects all `ReasoningResult` instances.
5. Records execution statistics (counts, timing, which rules ran).
6. Returns an immutable `AnalysisModel`.

If any rule raises an exception, the exception propagates immediately.
Rules run sequentially within a single call — no parallelism.

## EvidencePackageAssembler

```
assembler = EvidencePackageAssembler()
package = assembler.assemble(analysis)
```

The assembler groups `ReasoningResult` entries into EvidencePackage sections
by matching `finding_type` against known prefixes:

| Prefix | Section |
|---|---|
| `experience_` | relevant_experiences |
| `skill_` | matching_skills |
| `education_` | education |
| `strength_` | strengths |
| `weakness_` | weaknesses |
| `gap_` | missing_competencies |
| `recommendation_` | recommendations |

All results also populate `supporting_evidence`. Results with unmapped
finding types appear only in `supporting_evidence`.

## Key Properties

- **Immutable.** All data models use `@dataclass(frozen=True)`. Tuples
  replace lists. Dicts are defensively copied.
- **Deterministic.** Same graph + same registry = same AnalysisModel and
  same EvidencePackage. No randomness, no model inference.
- **No AI dependency.** The Reasoning Engine has no knowledge of AI
  providers, prompts, or model APIs.
- **Testable.** Every Rule is a pure function. The registry, engine, and
  assembler are independently testable without AI.
