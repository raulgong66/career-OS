"""ProfileQualityEngine — deterministic profile quality facade (M1.24.1).

The engine is an **orchestration-only facade** (ADR-009, M1.24.0
clarification). It does not implement rule logic, scoring algorithms, or graph
traversal. It composes existing Core capabilities:

- ``careeros.reasoning`` — the engine reuses the default rule registry through
  ``ReasoningEngine`` (AC 1.5). Exactly one knowledge graph is built per run,
  inside the Reasoning Engine (AC 1.11); this facade never builds a second one.
- ``careeros.profile_quality.dimensions`` — the nine pure dimension
  calculators aggregate deterministic ratios over the profile dict.
- ``careeros.resolution`` — resolution types are derived from the Resolution
  Engine's ``RESOLVABLE_RULES`` set (ADR-009 source mapping).

The facade operates **read-only** on the canonical profile dict and never
depends on Job Descriptions, Tailoring, Interview Intelligence, CSKS, the CLI,
or the API (strict profile-centric scope).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from careeros.reasoning import ReasoningEngine, RuleRegistry, create_default_registry

from .dimensions import DIMENSION_CALCULATORS, DIMENSION_WEIGHTS
from .report import (
    PROFILE_QUALITY_ENGINE_VERSION,
    Citation,
    DimensionScore,
    Finding,
    ProfileQualityReport,
)


@dataclass(frozen=True)
class ProfileQualityEngine:
    """Deterministic profile quality analysis facade.

    Role: orchestration only — delegates all rule execution to the Reasoning
    Engine and all resolution semantics to the Resolution Engine.
    """

    registry: RuleRegistry = field(default_factory=create_default_registry)

    def run(self, profile: dict[str, Any]) -> ProfileQualityReport:
        """Execute the orchestration pipeline and return a profile quality report.

        The same profile dict always produces the same health score, dimension
        scores, findings, and citations (AC 1.2 determinism guarantee).
        """
        reasoning_report = ReasoningEngine(self.registry).analyze(profile)

        dimension_scores: list[DimensionScore] = []
        findings: list[Finding] = []
        citations: list[Citation] = []

        for name, weight in DIMENSION_WEIGHTS.items():
            score, dim_findings, dim_citations = DIMENSION_CALCULATORS[name](profile)
            dimension_scores.append(
                DimensionScore(
                    name=name,
                    score=score,
                    weight=weight,
                    findings=tuple(dim_findings),
                    citations=tuple(dim_citations),
                )
            )
            findings.extend(dim_findings)
            citations.extend(dim_citations)

        aggregate = sum(dimension.score * dimension.weight for dimension in dimension_scores)
        health_score = int(round(aggregate * 100))

        return ProfileQualityReport(
            profile_id=reasoning_report.profile_id,
            profile_version=profile.get("profileVersion") or "",
            health_score=health_score,
            dimension_scores=tuple(dimension_scores),
            findings=tuple(findings),
            citations=_dedupe_citations(citations),
            generated_at=datetime.now(timezone.utc),
            engine_version=PROFILE_QUALITY_ENGINE_VERSION,
        )


def run_profile_quality(profile: dict[str, Any]) -> ProfileQualityReport:
    """Single-call profile quality analysis."""
    return ProfileQualityEngine().run(profile)


def _dedupe_citations(citations: list[Citation]) -> tuple[Citation, ...]:
    """Deduplicate citations preserving first-seen order (deterministic)."""
    seen: set[tuple[str, str, str, str]] = set()
    out: list[Citation] = []
    for citation in citations:
        key = (
            citation.entity_id,
            citation.entity_type,
            citation.property_path,
            citation.snippet,
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(citation)
    return tuple(out)


__all__ = ["ProfileQualityEngine", "run_profile_quality"]
