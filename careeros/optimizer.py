"""Evidence-based CV optimization engine for CareerOS."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Union

from .exceptions import ValidationError, EntityNotFoundError


@dataclass
class Recommendation:
    """A structured recommendation for optimizing a CV."""

    id: str
    type: str  # e.g., "skill", "experience", "achievement", "project", "education", "certification"
    operation: str  # "ADD", "UPDATE", "MOVE", "REMOVE"
    display_name: str
    details: dict[str, Any]
    evidence: list[dict[str, Any]] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert the recommendation to a dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "operation": self.operation,
            "display_name": self.display_name,
            "details": self.details,
            "evidence": self.evidence,
            "scores": self.scores,
        }


class CVOptimizer:
    """Optimizes CV artifacts by matching them against canonical profile elements."""

    def __init__(self, profile_data: dict[str, Any]) -> None:
        """Initialize the optimizer with canonical profile data.

        Args:
            profile_data: Dictionary containing the canonical profile data.
        """
        self.profile = profile_data

    def optimize_cv(self, artifact_id: str, job_description: Union[str, None] = None) -> list[Recommendation]:
        """Generate structured recommendations for a CV artifact.

        Args:
            artifact_id: The ID of the CV artifact to optimize.
            job_description: Optional job description text to prioritize recommendations.

        Returns:
            A list of Recommendation objects sorted by relevance score descending.
        """
        # Find the target artifact in the profile
        artifacts = self.profile.get("artifacts", [])
        target_artifact = None
        for art in artifacts:
            if art.get("id") == artifact_id:
                target_artifact = art
                break

        if not target_artifact:
            raise EntityNotFoundError(f"Artifact not found: {artifact_id}")

        # Check if it's a CV or resume
        art_type = target_artifact.get("artifactType", "").lower()
        if art_type not in {"cv", "resume"}:
            # We can still proceed but raise warning in logs/warnings if needed.
            pass

        # Identify items already referenced in the CV
        source_refs = target_artifact.get("sourceRefs", [])
        existing_ids = {ref.get("id") for ref in source_refs if ref.get("id")}

        # Extract target context and keyword emphasis
        target_context_emphases: list[str] = []
        target_context_refs = target_artifact.get("targetContextRefs", [])
        if target_context_refs:
            ctx_ids = {ref.get("id") for ref in target_context_refs if ref.get("id")}
            for ctx in self.profile.get("targetContexts", []):
                if ctx.get("id") in ctx_ids:
                    target_context_emphases.extend(ctx.get("emphasis") or [])

        # Process job description keywords
        jd_keywords = self._extract_keywords(job_description)

        # Categorized candidates from the profile that are not currently in the CV
        categories = {
            "skill": "skills",
            "experience": "experiences",
            "achievement": "achievements",
            "project": "projects",
            "education": "education",
            "certification": "certifications",
        }

        recommendations: list[Recommendation] = []

        for type_name, list_key in categories.items():
            elements = self.profile.get(list_key, [])
            for element in elements:
                element_id = element.get("id")
                if not element_id or element_id in existing_ids:
                    continue

                # Verify if supported by evidence
                backing_evidence = self._get_backing_evidence(element, type_name)
                if not backing_evidence:
                    continue  # Recommends ONLY additions supported by verified user data

                # Calculate display name
                display_name = self._get_display_name(element, type_name)

                # Compute weighted relevance scores
                scores = self._compute_scores(element, type_name, jd_keywords, target_context_emphases, len(backing_evidence))

                recommendations.append(
                    Recommendation(
                        id=element_id,
                        type=type_name,
                        operation="ADD",
                        display_name=display_name,
                        details=element,
                        evidence=backing_evidence,
                        scores=scores,
                    )
                )

        # Sort recommendations by weighted total score descending
        recommendations.sort(key=lambda r: r.scores.get("weighted_total", 0.0), reverse=True)
        return recommendations

    def _get_backing_evidence(self, element: dict[str, Any], element_type: str) -> list[dict[str, Any]]:
        """Get all evidence items backing a profile element."""
        element_id = element.get("id")
        if not element_id:
            return []

        direct_evidence_ids = {
            ref.get("id")
            for ref in element.get("evidenceRefs", [])
            if ref.get("id")
        }

        backing_evidence = []
        for ev in self.profile.get("evidence", []):
            ev_id = ev.get("id")
            if not ev_id:
                continue

            is_backing = ev_id in direct_evidence_ids

            if not is_backing:
                related_refs = ev.get("relatedRefs") or []
                for ref in related_refs:
                    if ref.get("id") == element_id:
                        ref_type = ref.get("type")
                        if not ref_type or ref_type.lower() == element_type.lower():
                            is_backing = True
                            break

            if is_backing:
                backing_evidence.append(ev)

        return backing_evidence

    def _get_display_name(self, element: dict[str, Any], element_type: str) -> str:
        """Get a user-friendly display name for an element."""
        if element_type == "skill":
            return str(element.get("name") or element.get("id"))
        elif element_type == "experience":
            title = element.get("title") or "Experience"
            org_names = []
            # Optionally resolve organization reference names
            for ref in element.get("organizationRefs", []):
                org_id = ref.get("id")
                for org in self.profile.get("organizations", []):
                    if org.get("id") == org_id and org.get("name"):
                        org_names.append(org["name"])
            org_suffix = f" at {', '.join(org_names)}" if org_names else ""
            return f"{title}{org_suffix}"
        elif element_type == "achievement":
            return str(element.get("statement") or element.get("id"))
        elif element_type == "project":
            return str(element.get("name") or element.get("id"))
        elif element_type == "education":
            prog = element.get("program") or "Education Program"
            field = element.get("fieldOfStudy")
            field_suffix = f" in {field}" if field else ""
            return f"{prog}{field_suffix}"
        elif element_type == "certification":
            return str(element.get("name") or element.get("id"))
        return str(element.get("id"))

    def _compute_scores(
        self,
        element: dict[str, Any],
        element_type: str,
        jd_keywords: set[str],
        target_context_emphases: list[str],
        evidence_count: int,
    ) -> dict[str, float]:
        """Compute the weighted scores for the recommendation."""
        # Aggregate all textual content in this element
        element_text = self._collect_element_text(element).lower()

        # 1. Job Description Match
        jd_match = 0.0
        if jd_keywords:
            matched_words = sum(1.0 for keyword in jd_keywords if keyword in element_text)
            # Normalize or return raw count (let's keep it as raw matches capped or scaled)
            jd_match = matched_words

        # 2. Target Context Match
        context_match = 0.0
        for emphasis in target_context_emphases:
            if emphasis.lower() in element_text:
                context_match += 1.0

        # 3. Evidence Strength
        # Count of distinct evidence items
        evidence_strength = float(evidence_count)

        # 4. Weighted Total
        # job_description_match * 2.0 + target_context_match * 1.5 + evidence_strength * 1.0
        weighted_total = (jd_match * 2.0) + (context_match * 1.5) + (evidence_strength * 1.0)

        return {
            "job_description_match": jd_match,
            "target_context_match": context_match,
            "evidence_strength": evidence_strength,
            "weighted_total": weighted_total,
        }

    def _collect_element_text(self, element: dict[str, Any]) -> str:
        """Recursively collect all string values in an element to use for keyword matching."""
        parts = []

        def recurse(val: Any) -> None:
            if isinstance(val, str):
                parts.append(val)
            elif isinstance(val, dict):
                for k, v in val.items():
                    if k not in {"id", "evidenceRefs", "organizationRefs", "projectRefs", "skillRefs", "achievementRefs", "contextRefs"}:
                        recurse(v)
            elif isinstance(val, list):
                for item in val:
                    recurse(item)

        recurse(element)
        return " ".join(parts)

    @staticmethod
    def _extract_keywords(text: Union[str, None]) -> set[str]:
        """Extract alphanumeric keywords from text, ignoring stopwords."""
        if not text:
            return set()
        tokens = re.findall(r"[a-zA-Z0-9_]{3,}", text.lower())
        stopwords = {
            "the", "and", "a", "an", "of", "to", "in", "for", "with", "on", "at", 
            "by", "from", "about", "as", "into", "like", "through", "after", "before", 
            "are", "is", "was", "were", "be", "been", "being", "have", "has", "had", 
            "having", "do", "does", "did", "doing", "can", "could", "will", "would", 
            "should", "shall", "must", "may", "might", "or", "but", "if", "then", 
            "else", "when", "where", "why", "how", "all", "any", "both", "each", 
            "few", "more", "most", "other", "some", "such", "no", "nor", "not", 
            "only", "own", "same", "so", "than", "too", "very", "just", "now",
            "this", "that", "your", "their", "its", "our", "you", "they", "them",
            "we", "him", "her", "his", "hers", "us", "me", "i", "my", "myself"
        }
        return {token for token in tokens if token not in stopwords}
