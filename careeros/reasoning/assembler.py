from __future__ import annotations

from typing import Any

from .models import AnalysisModel, EvidencePackage


class EvidencePackageAssembler:
    SECTION_PREFIXES: dict[str, str] = {
        "experience_": "relevant_experiences",
        "skill_": "matching_skills",
        "education_": "education",
        "strength_": "strengths",
        "weakness_": "weaknesses",
        "gap_": "missing_competencies",
        "recommendation_": "recommendations",
    }

    def assemble(self, analysis: AnalysisModel) -> EvidencePackage:
        sections: dict[str, list[dict[str, Any]]] = {
            "relevant_experiences": [],
            "matching_skills": [],
            "education": [],
            "strengths": [],
            "weaknesses": [],
            "missing_competencies": [],
            "recommendations": [],
        }

        evidence_list: list[dict[str, Any]] = []

        for result in analysis.reasoning_results:
            target = self._section_for(result.finding_type)
            if target is not None:
                sections[target].append(self._result_to_section_entry(result))
            evidence_list.append(self._result_to_evidence_entry(result))

        sorted_sections: dict[str, tuple[dict[str, Any], ...]] = {
            k: tuple(v) for k, v in sections.items()
        }

        candidate_summary = self._build_candidate_summary(analysis)

        meta: dict[str, Any] = {
            "generated_at": analysis.generated_at.isoformat(),
            "profile_id": analysis.profile_id,
            "reasoning_version": "1.0.0",
        }

        stats = analysis.execution_stats
        rule_summary: dict[str, Any] = {
            "total_rules_executed": stats.get("total_rules", 0),
            "total_findings_produced": stats.get("total_findings", 0),
            "execution_time_seconds": stats.get("execution_time_seconds", 0.0),
        }

        return EvidencePackage(
            meta=meta,
            candidate_summary=candidate_summary,
            relevant_experiences=sorted_sections["relevant_experiences"],
            matching_skills=sorted_sections["matching_skills"],
            education=sorted_sections["education"],
            strengths=sorted_sections["strengths"],
            weaknesses=sorted_sections["weaknesses"],
            missing_competencies=sorted_sections["missing_competencies"],
            recommendations=sorted_sections["recommendations"],
            supporting_evidence=tuple(evidence_list),
            rule_summary=rule_summary,
        )

    @classmethod
    def _section_for(cls, finding_type: str) -> str | None:
        for prefix, section in cls.SECTION_PREFIXES.items():
            if finding_type.startswith(prefix):
                return section
        return None

    @staticmethod
    def _result_to_section_entry(result: Any) -> dict[str, Any]:
        return {
            "finding_type": result.finding_type,
            "value": result.value,
            "confidence": result.confidence,
            "rule_id": result.rule_id,
        }

    @staticmethod
    def _result_to_evidence_entry(result: Any) -> dict[str, Any]:
        return {
            "evidence_id": f"{result.rule_id}-{result.finding_type}",
            "type": result.finding_type,
            "source": result.rule_id,
            "summary": str(result.value) if result.value is not None else "",
            "confidence": result.confidence,
            "references": list(result.evidence_refs),
        }

    @staticmethod
    def _build_candidate_summary(analysis: AnalysisModel) -> dict[str, Any]:
        profile = {}
        for r in analysis.reasoning_results:
            if r.finding_type == "total_years_of_experience":
                profile["total_years_of_experience"] = r.value
            elif r.finding_type == "highest_education":
                profile["highest_education"] = r.value
            elif r.finding_type == "career_stage_classification":
                profile["career_stage"] = r.value
        profile["total_findings"] = len(analysis.reasoning_results)
        return profile
