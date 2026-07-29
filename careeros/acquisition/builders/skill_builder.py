from __future__ import annotations

from typing import Any, ClassVar

from ..person_data import ExperienceData, SkillData
from .base import BaseBuilder, BuilderContext


SKILL_ALIASES: dict[str, str] = {
    "c#": "C#",
    "c sharp": "C#",
    "csharp": "C#",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "node": "Node.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "ms sql": "Microsoft SQL Server",
    "sql server": "Microsoft SQL Server",
    "mssql": "Microsoft SQL Server",
    "reactjs": "React",
    "react.js": "React",
    "vuejs": "Vue.js",
    "vue.js": "Vue.js",
    "nextjs": "Next.js",
    "next.js": "Next.js",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
}


class SkillBuilder(BaseBuilder):
    entity_type: ClassVar[type] = SkillData
    profile_key: ClassVar[str] = "skills"
    extraction_field: ClassVar[str] = "skills"

    def normalize(self, items: list) -> list:
        seen: set[str] = set()
        unique: list[SkillData] = []

        for skill in items:
            if not isinstance(skill, SkillData):
                continue
            normalized = self._normalize_one(skill)
            key = normalized.name.lower()
            if key not in seen:
                seen.add(key)
                unique.append(normalized)

        unique.sort(key=lambda s: s.name.lower())
        return unique

    def prepare(
        self,
        items: list,
        all_data: dict[type, list],
    ) -> list:
        experiences = all_data.get(ExperienceData, [])
        return self.associate_evidence(items, experiences)

    def build_many(
        self,
        items: list,
        context: BuilderContext,
    ) -> list[dict[str, Any]]:
        return [self._build_one(skill) for skill in items]

    def _normalize_one(self, skill: SkillData) -> SkillData:
        name = skill.name.strip()
        canonical = SKILL_ALIASES.get(name.lower(), name)
        return SkillData(
            name=canonical,
            category=skill.category.strip() if skill.category else None,
            proficiency=skill.proficiency.strip() if skill.proficiency else None,
            evidence=list(skill.evidence) if skill.evidence else [],
            confidence=skill.confidence,
            source_reference=skill.source_reference.strip() if skill.source_reference else None,
        )

    def associate_evidence(
        self,
        skills: list[SkillData],
        experiences: list[ExperienceData],
    ) -> list[SkillData]:
        result: list[SkillData] = []
        for skill in skills:
            evidence: list[dict] = list(skill.evidence)
            skill_lower = skill.name.lower()
            for exp in experiences:
                tech_lower = [t.lower() for t in exp.technologies]
                if skill_lower in tech_lower:
                    evidence.append({
                        "experienceId": exp.id,
                        "organization": exp.organization,
                        "title": exp.title,
                    })
            result.append(SkillData(
                name=skill.name,
                category=skill.category,
                proficiency=skill.proficiency,
                evidence=evidence,
                confidence=skill.confidence,
                source_reference=skill.source_reference,
            ))
        return result

    @staticmethod
    def _build_one(skill: SkillData) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "id": f"skill-{skill.name.lower().replace(' ', '-').replace('.', '-')}",
            "name": skill.name,
        }
        if skill.category:
            entry["category"] = skill.category
        ext: dict[str, Any] = {}
        if skill.proficiency:
            ext["proficiency"] = skill.proficiency
        if skill.evidence:
            ext["experienceEvidence"] = skill.evidence
        if ext:
            entry["extensions"] = ext
        return entry
