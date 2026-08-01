"""Interview Intelligence — competency mapping.

``CompetencyMapper`` builds ``Competency`` objects as a deterministic *view*
over canonical profile skills and the Core concept taxonomy
(``careeros.optimizer.CONCEPT_TAXONOMY``). There is deliberately **no parallel
competency database**: a competency references canonical skill ids and concept
taxonomy ids, and cites the canonical elements (skill + experiences) that
substantiate it.
"""

from __future__ import annotations

from typing import Any

from careeros.knowledge import KnowledgeGraph

from ..optimizer import CONCEPT_TAXONOMY
from .domain import Competency, EvidenceCitation

_IGNORED_SKILL_TOKENS: frozenset[str] = frozenset(
    {
        "and", "for", "the", "with", "using", "via", "based", "native",
        "management", "engineering", "services", "platform", "solutions",
        "infrastructure",
    }
)


class CompetencyMapper:
    """Map canonical profile skills to competencies enriched by Core concepts."""

    def map(
        self,
        profile: dict[str, Any],
        graph: KnowledgeGraph | None = None,
    ) -> tuple[Competency, ...]:
        """Build competencies, one per canonical skill (deterministic order)."""
        skills = sorted(
            (skill for skill in profile.get("skills", []) if skill.get("id") and skill.get("name")),
            key=lambda skill: skill.get("id", ""),
        )
        competencies: list[Competency] = []
        for skill in skills:
            skill_id = skill["id"]
            name = skill["name"]
            concept_ids = self.match_concepts(name, skill.get("description", ""))
            category = skill.get("category") or self._category_for(concept_ids)
            evidence = self._skill_evidence(skill, graph)
            competencies.append(
                Competency(
                    id=f"competency-{skill_id}",
                    name=name,
                    category=category,
                    skill_ids=(skill_id,),
                    concept_ids=tuple(concept_ids),
                    evidence=tuple(evidence),
                )
            )
        return tuple(competencies)

    @staticmethod
    def match_concepts(name: str, description: str = "") -> list[str]:
        """Match a skill to Core concept-taxonomy ids via alias substrings."""
        haystack = f"{name} {description}".lower()
        matched: list[str] = []
        for concept in sorted(CONCEPT_TAXONOMY, key=lambda item: item.id):
            if any(alias.lower() in haystack for alias in concept.aliases):
                matched.append(concept.id)
        return matched

    @staticmethod
    def _category_for(concept_ids: list[str]) -> str:
        for concept in CONCEPT_TAXONOMY:
            if concept.id in concept_ids:
                return concept.category
        return "general"

    def _skill_evidence(
        self,
        skill: dict[str, Any],
        graph: KnowledgeGraph | None,
    ) -> list[EvidenceCitation]:
        citations = [
            EvidenceCitation(
                element_type="skill",
                element_id=skill["id"],
                quote=skill.get("name"),
            )
        ]
        if graph is None:
            return citations
        for experience_node in sorted(
            graph.experiences_using(skill["name"]), key=lambda node: node.id
        ):
            citations.append(
                EvidenceCitation(
                    element_type="experience",
                    element_id=experience_node.id,
                    quote=experience_node.properties.get("scope") or experience_node.label,
                )
            )
        return citations

    @staticmethod
    def skill_tokens(skill: dict[str, Any]) -> list[str]:
        """Distinctive tokens of a skill (name + description) for experience matching.

        Deterministic: lowercased, non-alphanumeric-split, length >= 3,
        common words removed, de-duplicated, sorted.
        """
        import re

        text = f"{skill.get('name', '')} {skill.get('description', '')}"
        tokens: set[str] = set()
        for match in re.findall(r"[a-z0-9]+", text.lower()):
            if len(match) >= 3 and match not in _IGNORED_SKILL_TOKENS:
                tokens.add(match)
        return sorted(tokens)
