from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from careeros.knowledge import KnowledgeGraph, KnowledgeGraphBuilder

from .models import AnalysisModel, Evidence, ReasoningReport, ReasoningResult, RuleContext
from .findings import ProfileRecommendations
from .registry import RuleRegistry


class ReasoningEngine:
    def __init__(self, registry: RuleRegistry) -> None:
        self._registry = registry

    @property
    def registry(self) -> RuleRegistry:
        return self._registry

    def analyze(
        self,
        profile: dict[str, Any],
        parameters: dict[str, Any] | None = None,
    ) -> ReasoningReport:
        graph = KnowledgeGraphBuilder().build(profile)
        analysis = self.run(graph, profile=profile, parameters=parameters)

        findings_by_type: dict[str, list[ReasoningResult]] = {}
        for f in analysis.reasoning_results:
            findings_by_type.setdefault(f.finding_type, []).append(f)

        confidence_dist: dict[str, int] = {}
        for f in analysis.reasoning_results:
            key = str(f.confidence)
            confidence_dist[key] = confidence_dist.get(key, 0) + 1

        summary: dict[str, Any] = {
            "total_findings": len(analysis.reasoning_results),
            "findings_by_type_count": {
                k: len(v) for k, v in findings_by_type.items()
            },
            "total_rules_executed": analysis.execution_stats.get("total_rules", 0),
            "confidence_distribution": confidence_dist,
            "execution_time_seconds": analysis.execution_stats.get(
                "execution_time_seconds", 0.0
            ),
        }

        return ReasoningReport(
            engine_version="1.0.0",
            generated_at=analysis.generated_at,
            profile_id=analysis.profile_id,
            findings=analysis.reasoning_results,
            findings_by_type={k: tuple(v) for k, v in findings_by_type.items()},
            recommendations=ProfileRecommendations.from_findings(
                analysis.reasoning_results
            ).items,
            summary=summary,
            execution_stats=dict(analysis.execution_stats),
        )

    def run(
        self,
        graph: KnowledgeGraph,
        profile: dict[str, Any] | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> AnalysisModel:
        start = datetime.now(timezone.utc)
        context = RuleContext(
            graph=graph,
            profile=profile or {},
            parameters=parameters or {},
        )

        profile_id = self._resolve_profile_id(profile)
        order = self._registry.execution_order()
        all_results: list[ReasoningResult] = []
        executed: dict[str, list[ReasoningResult]] = {}

        for rule in order:
            results = rule.execute(context)
            executed[rule.id] = results
            all_results.extend(results)

        end = datetime.now(timezone.utc)
        elapsed = (end - start).total_seconds()

        stats: dict[str, Any] = {
            "total_rules": len(order),
            "total_findings": len(all_results),
            "execution_time_seconds": elapsed,
            "rules_executed": [r.id for r in order],
            "findings_per_rule": {
                rid: len(res) for rid, res in executed.items()
            },
            "started_at": start.isoformat(),
            "completed_at": end.isoformat(),
        }

        return AnalysisModel(
            profile_id=profile_id,
            generated_at=end,
            reasoning_results=tuple(all_results),
            evidence=(),
            evidence_sets=(),
            execution_stats=stats,
        )

    @staticmethod
    def _resolve_profile_id(profile: dict[str, Any] | None) -> str:
        if profile is None:
            return "unknown"
        person = profile.get("person", {})
        pid: str = person.get("id", "unknown")
        return pid
