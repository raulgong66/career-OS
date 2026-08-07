# ADR 009: Unified Deterministic Recommendation Model

## Status

Accepted (M1.24)

## Context

CareerOS produces recommendations from two independent mechanisms:

- **Reasoning Engine** (`careeros/reasoning`) — runs 31 rules (including 8 profile-quality rules in `recommendation_rules.py`) and returns profile recommendations grouped by title and `triggeredRule`. Each carries `title`, `reason`, `explanation`, `suggested_action`, `examples`, `recruiter_impact`, and `missing_info[]`, and supports actions `Review | Dismiss | GoTo Section | Resolve`.
- **CVOptimizer** (`careeros/optimizer.py`) — performs artifact-vs-Job-Description gap analysis and returns a flat list of ADD recommendations, each with `id`, `type`, `displayName`, `details`, `evidence`, and `scores{jd_match, context_match, evidence_str}`. These have no resolve actions.

Today these operate independently: 8 profile-quality rules (structural profile health) and 6 element-type ADD recommendations (CV gap analysis) run with **no unified pipeline, no shared metrics, and no cross-consumer reuse**.

Multiple recommendation implementations become problematic:

- **Duplicated recommendation rendering logic.** Tailoring has custom rendering for two different recommendation shapes.
- **Inconsistent action sets.** Profile recommendations offer Review/Dismiss/Resolve/GoTo; optimization recommendations offer no actions at all.
- **No shared component.** The rendering cannot be reused in the Workspace, CSKS, CLI, or future pages.
- **Resolution is only reachable from Tailoring.** The 4 resolvable rules cannot be addressed from the Artifact Workspace or other consumers.
- **No unified "Improvement Queue" concept.** Users cannot see all pending improvements in one place.

The **Resume Generation Workspace** requires a unified recommendation pipeline because its core experience — a prioritized, filterable **Improvement Queue** surfaced alongside the Health dashboard, Resolution workflow, Template Preview, and artifact generation — must consume a single list of all findings (profile-quality and, when a JD is provided, optimization) with resolution actions keyed off each item. A shared, normalized model is a precondition for reusing that experience across Tailoring, Interview Intelligence, and future workspaces instead of duplicating per-page recommendation UIs.

## Decision

CareerOS adopts a **single deterministic Recommendation Model shared across workspaces**.

The model is consumed by:

- Resume Workspace
- Tailoring
- Interview Intelligence
- Future Learning Workspace
- Future Career Analytics

The recommendation model **must remain deterministic and fully explainable**.

### Unified Recommendation Shape

A single internal shape normalizes every source:

```
UnifiedRecommendation:
  id: str                          # stable ID
  source: "profile_quality" | "optimization"   # provenance
  rule_id: str                     # e.g., "recommendation_add_measurable_achievement"
  element_id: str                  # profile element ID
  element_type: str                # "experience" | "skill" | "project" | ...
  title: str                       # human-readable title
  reason: str                      # why this matters
  suggested_action: str            # deterministic action text
  resolution_type: "auto" | "guided" | "none"   # can Resolution Engine fix it?
  evidence_refs: list[str]         # evidence IDs backing this recommendation
  priority: "high" | "medium" | "low"
  estimated_impact: "high" | "medium" | "low"
  confidence: "high" | "medium" | "low"
  # Optimization-specific (optional, None for profile_quality):
  jd_match_score: float | None
  context_match_score: float | None
  weighted_total: float | None
```

### Source Mapping

| Source | `source` | `resolution_type` | Extra fields |
|---|---|---|---|
| `ReasoningResult` (profile-quality) | `"profile_quality"` | `"auto"` for the 4 resolvable rules, `"guided"` for others | None |
| `OptimizationResult.Recommendation` | `"optimization"` | `"none"` (ADD only) | `jd_match_score`, `context_match_score`, `weighted_total` |

### Deduplication

Recommendations are deduplicated by the key `(rule_id, element_id)`. If both sources produce the same key, `profile_quality` wins, because the structural fix it represents enables the optimization.

### Unified API Response

Endpoints returning recommendations use a single envelope:

```
{
  "profile_quality_report": { ... },
  "recommendations": [ UnifiedRecommendation, ... ],
  "optimization_result": { ... }   // present only when a Job Description is provided
}
```

The Workspace UI consumes the single `recommendations` array and renders actions according to each item's `resolution_type`.

## Responsibilities

| Component | Responsibilities |
|---|---|
| **ProfileQualityEngine** | Evaluates canonical profiles (read-only); computes the 8 deterministic health dimensions; produces deterministic findings via the existing Reasoning Engine; emits recommendations via the existing Resolution Engine for the 4 resolvable rules. It is a **facade** — it introduces orchestration, not new business rules, and reuses rather than replaces Reasoning Engine, Resolution Engine, EvidenceSelector, ExportContract, and CSKS. |
| **Resume Workspace** | Displays recommendations (Improvement Queue); groups/filters them by dimension, priority, and resolvability; resolves recommendations through the shared Resolution workflow; previews changes via Template Preview; generates artifacts. It consumes the unified model; it does not evaluate profile quality. |
| **Tailoring** | Consumes the unified recommendations; augments them with Job Description analysis via CVOptimizer when a JD is provided; **never owns profile-quality evaluation**. Tailoring may call ProfileQualityEngine and then call CVOptimizer; neither engine depends on the other. |

## Architectural Principles

- **Canonical Profile remains the single source of truth.** Recommendations are derived from it (per ADR-004); it is never versioned by this model.
- **Recommendations are derived artifacts.** They are normalized, derived outputs of deterministic analysis and are not first-class profile data.
- **No AI-only recommendations.** All rules are pure functions on the profile dict — no LLM, no embeddings, no fuzzy matching (consistent with ADR-006).
- **Every recommendation must be explainable.** Each carries `title`, `reason`, and `suggested_action`.
- **Every recommendation must be traceable to deterministic evidence.** Each carries `evidence_refs` and citations referencing canonical elements.
- **Preview is render-only.** Preview is the fastest path and must never have side effects — no persistence, no artifact creation, no profile mutation, no exports, no version creation, no tailoring context, no background processing.
- **Artifact history is separate from Canonical Profile history.** Versioning belongs to generated artifacts and Workspace history; artifact history must not mutate canonical profile history, and ProfileQualityEngine never versions profiles.

## Consequences

**Positive:**

- **Reusable across workspaces.** The engine runs once per profile; consumers read the cached report instead of re-executing per consumer.
- **Deterministic.** Same profile dict produces identical findings, recommendations, and health scores every run.
- **Consistent UX.** A single shared recommendation component and action model replace two divergent rendering patterns.
- **Simplified maintenance.** One normalization layer and one shared component instead of per-page custom rendering.
- **Easier testing.** Source mapping and deduplication by `(rule_id, element_id)` are unit-testable in isolation.
- **Shared APIs.** One unified response envelope and one improvement-queue endpoint serve the Workspace, Tailoring, CSKS, CLI, and future consumers.

**Trade-offs:**

- The source-mapping table must be maintained as new recommendation sources are added.
- Deduplication edge cases require comprehensive tests; on conflict `profile_quality` is preferred by policy.
- Profile Quality Engine and CVOptimizer are complementary but must stay clearly separated to avoid duplicated logic.
- `UnifiedRecommendation` carries optimization-specific optional fields that are `None` for profile-quality items.
- The unified API/UI requires incremental extraction of shared frontend components (e.g. `RecommendationCard`, `ResolutionPanel`), which is deliberate, not free.
- Resolution continues to mutate the canonical profile in place; the audit trail must be extended to preserve full traceability.

## Alternatives Considered

| Alternative | Rejected Because |
|---|---|
| **Separate recommendation engine per workspace** | ProfileQualityEngine is a facade over existing deterministic capabilities — it introduces orchestration, not new business rules, and must not become another reasoning engine. A per-workspace engine would add a second rule registry or a parallel engine pipeline, duplicate reasoning, and reintroduce inconsistent UX. |
| **AI-generated recommendations without deterministic evidence** | Contradicts the deterministic, citable-output requirement. No AI, no embeddings, no fuzzy matching; every recommendation must be explainable and traceable to deterministic evidence (ADR-006). |
| **Embedding recommendation logic inside Resume Workspace** | Consumers depend on ProfileQualityEngine, never the reverse; the engine must not import any consumer (Workspace, Tailoring, Interview, CSKS, CLI), and the Workspace is a Module that consumes Core. Embedding would couple a Module to evaluation logic and violate the ADR-004 dependency flow (Frontend → API → Domain). |

## Relationships

- **Builds on**: ADR 0005 — Professional Knowledge Reasoning Layer (`docs/adr/0005-professional-knowledge-reasoning-layer.md`; rules produce deterministic findings). The Unified Recommendation Model normalizes the deterministic outputs that flow from that layer rather than redefining its rule/finding contract. Also builds on ADR-004 (Core boundaries — ProfileQualityEngine is Core; Workspace is a Module), ADR-006 (AI provider agnostic — deterministic only), ADR-007 (Interview Simulation is a consumer), ADR-008 (CSKS surfaces the same findings via its query layer and remains authoritative for "what changed in my profile?").
- **Consistent with**: ADR-005 — Interview Intelligence Module (`docs/platform-beta/interview-intelligence/ADR-005-Interview-Intelligence-Module.md`; a Core consumer module with no duplicate reasoning; it consumes the shared recommendation model).
- **Sources**: `docs/platform-beta/M1.24-Resume-Generation-Workspace-Discovery.md`, `docs/platform-beta/M1.24-Resume-Generation-Workspace-Spec.md`, and the M1.24.0 Architecture Finalization clarifications (facade scope, strict profile-centric scope, render-only preview contract, artifact-only versioning).

## Implementation Notes

- Implementation begins in **M1.24.1** (Profile Quality Engine + Health Score). Implementation details are not prescribed here; they are specified in the M1.24 Discovery and Specification documents.

## Decision Log

| Date | Decision |
|---|---|
| 2026-08-04 | M1.24.0 Architecture Finalization adopts the unified deterministic recommendation model: ProfileQualityEngine is a facade (orchestration only, no new business rules); scope is strictly profile-centric; preview is render-only; artifact versioning is separate from canonical profile history. |

---

*This ADR is immutable once accepted. Amendments require a new ADR.*
