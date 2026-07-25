"""Evidence-based CV optimization engine for CareerOS."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Union

from .exceptions import ValidationError, EntityNotFoundError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Requirement extraction configuration
# ---------------------------------------------------------------------------

# Structural phrase patterns (generic, not hardcoded phrases)
_SLASH_COMPOUND_RE = re.compile(r"\b[\w]+/[\w/]+\b")  # CI/CD, ML/AI
_CAPITALIZED_SEQUENCE_RE = re.compile(
    r"\b([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)+)\b"
)  # Azure DevOps, Zero Trust

# Curated vocabulary: common multi-word technical phrases (lowercased).
# Kept small — generic patterns above catch most phrases.
_KNOWN_PHRASES: list[str] = [
    "infrastructure as code",
    "site reliability engineering",
    "machine learning",
    "deep learning",
    "natural language processing",
    "computer vision",
    "platform engineering",
    "incident management",
    "vulnerability management",
    "threat modeling",
    "penetration testing",
    "identity and access management",
    "continuous integration",
    "continuous deployment",
    "continuous delivery",
    "application security",
    "cloud security",
    "network security",
    "container orchestration",
    "software engineering",
    "data engineering",
    "data science",
]

# Alias normalization: maps tokens / phrases to their canonical form.
_REQUIREMENT_ALIASES: dict[str, str] = {
    "k8s": "kubernetes",
    "python3": "python",
    "js": "javascript",
    "ts": "typescript",
    "gcp": "google cloud platform",
    "aws": "amazon web services",
    "iac": "infrastructure as code",
    "sre": "site reliability engineering",
    "iam": "identity and access management",
    "ml": "machine learning",
    "dl": "deep learning",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "devops": "devops",
    "devsecops": "devsecops",
    "mlops": "machine learning operations",
    "gitops": "gitops",
    "infra": "infrastructure",
    "microservices": "microservices",
    "observability": "observability",
}

# Stop words: common English + JD filler terms that are not meaningful requirements.
_STOP_WORDS: set[str] = {
    # Standard English stop words
    "the", "and", "a", "an", "of", "to", "in", "for", "with", "on", "at",
    "by", "from", "about", "as", "into", "like", "through", "after", "before",
    "are", "is", "was", "were", "be", "been", "being", "have", "has", "had",
    "having", "do", "does", "did", "doing", "can", "could", "will", "would",
    "should", "shall", "must", "may", "might", "or", "but", "if", "then",
    "else", "when", "where", "why", "how", "all", "any", "both", "each",
    "few", "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "just", "now",
    "this", "that", "your", "their", "its", "our", "you", "they", "them",
    "we", "him", "her", "his", "hers", "us", "me", "i", "my", "myself",
    # JD filler — words that appear in job descriptions but are not requirements
    "experience", "knowledge", "ability", "abilities", "skills", "skill",
    "required", "preferred", "qualifications", "responsibilities",
    "looking", "role", "position", "team", "work", "working",
    "years", "year", "plus", "bonus", "etc", "well", "also", "including",
    "strong", "understanding", "familiar", "proficient", "excellent",
    "demonstrated", "proven", "minimum", "bachelor", "master", "degree",
    "certification", "competitive", "benefits", "salary", "compensation",
    "company", "about", "join", "apply", "interested", "ideal",
    "candidates", "candidate", "individual", "individuals",
    "opportunity", "opportunities", "environment", "environments",
    "across", "within", "alongside", "between",
    "new", "existing", "multiple", "various", "different",
    "best", "practices", "practice",
    "ability", "track", "record", "related", "field",
    "least", "equivalent",
    "senior", "junior", "lead", "principal", "staff",
    "engineer", "engineers", "engineering",
    "developer", "developers", "development",
    "architect", "architecture", "architectures",
    "specialist", "analyst", "manager", "director",
    "familiarity", "exposure", "background",
    "verbal", "written", "communication",
    "problem", "solving", "analytical",
    "self", "motivated", "detail", "oriented",
    "fast", "paced", "deadline", "deadlines",
    "pipeline", "pipelines", "tooling", "toolchain",
    "platforms", "toolsets", "toolsets",
    # Swedish stop words (common function words)
    "och", "att", "det", "i", "en", "ett", "som", "är", "för", "med",
    "till", "av", "den", "har", "de", "inte", "om", "var", "men", "kan",
    "ska", "vi", "du", "han", "hon", "sig", "så", "nu", "här", "där",
    "upp", "ner", "ut", "in", "över", "under", "mellan", "från", "efter",
    "innan", "också", "bara", "redan", "än", "vad", "vem", "hur", "då",
    "dock", "tyvärr", "även", "alltså", "själv", "samt", "helt",
    "andra", "mycket", "mer", "än", "samma", "egen",
    # Swedish JD filler
    "erfarenhet", "kunskap", "kunskaper", "vana", "goda", "god",
    "flera", "år", "dokumenterad", "förmåga", "behärskar",
    "obehindrat", "praktisk", "djup", "omfattande",
    "sök", "ansök", "rollen", "tjänsten", "arbetsuppgifter",
    "kvalifikationer", "krav", "önskvärt", "meriterande",
    # Swedish JD responsibility verbs (duties, not requirements)
    "ansvara", "ansvarig", "arbeta", "arbetar", "bygga", "bygger",
    "coacha", "driva", "driver", "etablera", "etablerar",
    "implementera", "implementerar", "införa", "inför",
    "säkerställa", "säkerställer", "vidareutveckla", "vidareutvecklar",
    "utvärdera", "utvärderar", "sprida", "sprider",
    "samarbeta", "samarbetar", "kommunicera", "kommunicerar",
    "hantera", "hanterar", "delta", "deltar",
    "efterlevs", "efterleva",
    "omvärldsbevaka", "omvärldsbevakar",
    "förbättringsprojekt", "förändringsprojekt",
    "leveransprocess", "utvecklingsflödet",
    "systemutveckling", "principer", "ceremonier",
    "relaterade", "beroenden",
    "skalbar", "effektiv", "modern", "komplexa",
    "trygg", "behörig",
}

# Words that may start a sentence or job title but are not requirements.
_SEQUENCE_BLACKLIST: set[str] = {
    "senior", "junior", "lead", "principal", "staff", "associate",
    "we", "our", "the", "this", "you", "they", "he", "she",
    "looking", "seeking", "finding", "someone", "who",
}

# Regex for extracting single-word tokens from text.
# Uses \w to support Unicode word characters (Swedish ä, ö, å, etc.).
_TOKEN_RE = re.compile(r"\w{3,}")


class OptimizationStatus(str, Enum):
    """Semantic status of an optimization result."""

    ALREADY_COMPLETE = "already_complete"
    NO_MATCHES = "no_matches"
    RECOMMENDATIONS_AVAILABLE = "recommendations_available"


@dataclass
class OptimizationSummary:
    """Factual metrics about the tailoring analysis.

    All fields are computed deterministically from the profile and optimizer
    algorithm. No values are estimated or fabricated.
    """

    # Profile coverage
    total_profile_elements: int
    included_profile_elements: int
    profile_coverage: float
    additional_evidence: int

    # Profile analysis
    skills_evaluated: int
    experiences_evaluated: int
    projects_evaluated: int
    achievements_evaluated: int
    certifications_evaluated: int
    education_evaluated: int

    # Job analysis (only populated when job_description is provided)
    requirements_detected: int | None = None
    requirements_matched: int | None = None
    requirement_coverage: float | None = None
    matched_requirements: list[str] = field(default_factory=list)
    target_context_emphasis: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_profile_elements": self.total_profile_elements,
            "included_profile_elements": self.included_profile_elements,
            "profile_coverage": self.profile_coverage,
            "additional_evidence": self.additional_evidence,
            "skills_evaluated": self.skills_evaluated,
            "experiences_evaluated": self.experiences_evaluated,
            "projects_evaluated": self.projects_evaluated,
            "achievements_evaluated": self.achievements_evaluated,
            "certifications_evaluated": self.certifications_evaluated,
            "education_evaluated": self.education_evaluated,
            "requirements_detected": self.requirements_detected,
            "requirements_matched": self.requirements_matched,
            "requirement_coverage": self.requirement_coverage,
            "matched_requirements": self.matched_requirements,
            "target_context_emphasis": self.target_context_emphasis,
        }


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


@dataclass
class OptimizationResult:
    """Structured result of a CV optimization run."""

    status: OptimizationStatus
    recommendations: list[Recommendation] = field(default_factory=list)
    message: str = ""
    summary: OptimizationSummary | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "message": self.message,
            "summary": self.summary.to_dict() if self.summary else None,
        }


class CVOptimizer:
    """Optimizes CV artifacts by matching them against canonical profile elements."""

    def __init__(self, profile_data: dict[str, Any]) -> None:
        """Initialize the optimizer with canonical profile data.

        Args:
            profile_data: Dictionary containing the canonical profile data.
        """
        self.profile = profile_data

    def optimize_cv(self, artifact_id: str, job_description: Union[str, None] = None) -> OptimizationResult:
        """Generate structured recommendations for a CV artifact.

        Args:
            artifact_id: The ID of the CV artifact to optimize.
            job_description: Optional job description text to prioritize recommendations.

        Returns:
            An OptimizationResult with status, recommendations, and message.
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

        logger.info("=== OPTIMIZER DIAGNOSTICS ===")
        logger.info("Artifact: %s", artifact_id)
        logger.info("sourceRefs count: %d", len(existing_ids))
        logger.info("Existing IDs already in CV: %s", sorted(existing_ids))

        # Extract target context and keyword emphasis
        target_context_emphases: list[str] = []
        target_context_refs = target_artifact.get("targetContextRefs", [])
        if target_context_refs:
            ctx_ids = {ref.get("id") for ref in target_context_refs if ref.get("id")}
            for ctx in self.profile.get("targetContexts", []):
                if ctx.get("id") in ctx_ids:
                    target_context_emphases.extend(ctx.get("emphasis") or [])

        # Process job description requirements
        jd_requirements = self._extract_requirements(job_description)

        logger.info("Job description requirements extracted: %d", len(jd_requirements))
        logger.info("Target context emphases: %s", target_context_emphases)

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
        has_unreferenced_elements = False

        for type_name, list_key in categories.items():
            elements = self.profile.get(list_key, [])
            skipped_existing = 0
            skipped_no_id = 0
            skipped_no_evidence = 0
            added = 0
            for element in elements:
                element_id = element.get("id")
                if not element_id:
                    skipped_no_id += 1
                    continue
                if element_id in existing_ids:
                    skipped_existing += 1
                    continue

                has_unreferenced_elements = True

                # Verify if supported by evidence
                backing_evidence = self._get_backing_evidence(element, type_name)
                if not backing_evidence:
                    skipped_no_evidence += 1
                    continue  # Recommends ONLY additions supported by verified user data

                # Calculate display name
                display_name = self._get_display_name(element, type_name)

                # Compute weighted relevance scores
                scores = self._compute_scores(element, type_name, jd_requirements, target_context_emphases, len(backing_evidence))

                added += 1
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

            logger.info(
                "Category '%s': %d total, %d already in CV, %d no id, %d no evidence, %d added",
                type_name, len(elements), skipped_existing, skipped_no_id, skipped_no_evidence, added,
            )

        # Determine semantic status
        if not has_unreferenced_elements:
            status = OptimizationStatus.ALREADY_COMPLETE
            message = "This resume already includes all relevant evidence available in your CareerOS profile. No additional skills, experiences, projects, or certifications need to be added for this opportunity."
        elif not recommendations:
            status = OptimizationStatus.NO_MATCHES
            message = "The job description was analyzed successfully, but no additional relevant evidence was found in your CareerOS profile."
        else:
            status = OptimizationStatus.RECOMMENDATIONS_AVAILABLE
            message = ""

        # Sort recommendations by weighted total score descending
        recommendations.sort(key=lambda r: r.scores.get("weighted_total", 0.0), reverse=True)

        # Compute summary
        summary = self._compute_summary(
            artifact_id=artifact_id,
            existing_ids=existing_ids,
            recommendations=recommendations,
            jd_requirements=jd_requirements,
            target_context_emphasis=target_context_emphases,
        )

        logger.info("Optimization status: %s, total recommendations: %d", status.value, len(recommendations))
        logger.info("=== END DIAGNOSTICS ===")

        return OptimizationResult(
            status=status,
            recommendations=recommendations,
            message=message,
            summary=summary,
        )

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
        jd_requirements: list[str],
        target_context_emphases: list[str],
        evidence_count: int,
    ) -> dict[str, float]:
        """Compute the weighted scores for the recommendation."""
        # Aggregate all textual content in this element
        element_text = self._collect_element_text(element).lower()

        # 1. Job Description Match
        jd_match = 0.0
        if jd_requirements:
            matched_count = sum(1.0 for req in jd_requirements if req in element_text)
            jd_match = matched_count

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

    def _compute_summary(
        self,
        artifact_id: str,
        existing_ids: set[str],
        recommendations: list[Recommendation],
        jd_requirements: list[str],
        target_context_emphasis: list[str],
    ) -> OptimizationSummary:
        """Compute factual summary metrics about the optimization analysis.

        All values are derived deterministically from the profile data and
        optimizer algorithm. No values are estimated or fabricated.
        """
        categories = {
            "skills": ("skill", []),
            "experiences": ("experience", []),
            "projects": ("project", []),
            "achievements": ("achievement", []),
            "certifications": ("certification", []),
            "education": ("education", []),
        }

        total_profile_elements = 0
        included_profile_elements = 0

        for list_key, (type_name, _) in categories.items():
            elements = self.profile.get(list_key, [])
            for element in elements:
                element_id = element.get("id")
                if not element_id:
                    continue
                total_profile_elements += 1
                if element_id in existing_ids:
                    included_profile_elements += 1

        profile_coverage = (
            (included_profile_elements / total_profile_elements * 100.0)
            if total_profile_elements > 0
            else 0.0
        )

        # Job analysis: count how many JD requirements are matched in ANY profile element
        requirements_detected = len(jd_requirements) if jd_requirements else None
        requirements_matched: int | None = None
        requirement_coverage: float | None = None
        matched_reqs: set[str] = set()

        if jd_requirements:
            # Check all profile elements for requirement matches
            for list_key in categories:
                for element in self.profile.get(list_key, []):
                    element_text = self._collect_element_text(element).lower()
                    for req in jd_requirements:
                        if req in element_text:
                            matched_reqs.add(req)
            requirements_matched = len(matched_reqs)
            requirement_coverage = (
                (requirements_matched / requirements_detected * 100.0)
                if requirements_detected > 0
                else 0.0
            )

        # Collect top matched requirements sorted alphabetically, capped at 10
        top_matched = sorted(matched_reqs)[:10] if jd_requirements else []

        return OptimizationSummary(
            total_profile_elements=total_profile_elements,
            included_profile_elements=included_profile_elements,
            profile_coverage=round(profile_coverage, 1),
            additional_evidence=len(recommendations),
            skills_evaluated=len(self.profile.get("skills", [])),
            experiences_evaluated=len(self.profile.get("experiences", [])),
            projects_evaluated=len(self.profile.get("projects", [])),
            achievements_evaluated=len(self.profile.get("achievements", [])),
            certifications_evaluated=len(self.profile.get("certifications", [])),
            education_evaluated=len(self.profile.get("education", [])),
            requirements_detected=requirements_detected,
            requirements_matched=requirements_matched,
            requirement_coverage=round(requirement_coverage, 1) if requirement_coverage is not None else None,
            matched_requirements=top_matched,
            target_context_emphasis=target_context_emphasis,
        )

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
    def _extract_requirements(text: Union[str, None]) -> list[str]:
        """Extract normalized job requirements from text.

        Detection strategy (generic patterns + small curated vocabulary):
        1. Structural phrases — slash-compounds (CI/CD) and capitalized
           multi-word sequences (Azure DevOps) are extracted generically.
        2. Known phrases — a small curated list catches common lowercase
           technical phrases (infrastructure as code, machine learning).
        3. Single tokens — remaining words are filtered through an expanded
           stop-word list and normalized via an alias map.

        Returns a sorted, deduplicated list of requirement strings.
        """
        if not text:
            return []

        lowered = text.lower()

        # --- Phase 1: structural phrase extraction ---
        phrase_spans: list[tuple[int, int]] = []
        requirements: set[str] = set()

        # Slash-compounds: CI/CD, ML/AI, Terraform/Bicep/ARM
        for match in _SLASH_COMPOUND_RE.finditer(text):
            phrase_spans.append((match.start(), match.end()))
            token = match.group().lower()
            normalized = _REQUIREMENT_ALIASES.get(token, token)
            requirements.add(normalized)
            # Also emit individual components so they can match profile text
            for part in token.split("/"):
                part = part.strip()
                if len(part) >= 3 and part not in _STOP_WORDS:
                    part_norm = _REQUIREMENT_ALIASES.get(part, part)
                    requirements.add(part_norm)

        # Capitalized multi-word sequences: Azure DevOps, Zero Trust
        for match in _CAPITALIZED_SEQUENCE_RE.finditer(text):
            phrase_text = match.group()
            first_word = phrase_text.split()[0].lower()
            if first_word in _SEQUENCE_BLACKLIST:
                continue
            phrase_spans.append((match.start(), match.end()))
            token = phrase_text.lower()
            normalized = _REQUIREMENT_ALIASES.get(token, token)
            requirements.add(normalized)

        # --- Phase 2: known phrase extraction ---
        for phrase in _KNOWN_PHRASES:
            idx = lowered.find(phrase)
            while idx != -1:
                phrase_spans.append((idx, idx + len(phrase)))
                normalized = _REQUIREMENT_ALIASES.get(phrase, phrase)
                requirements.add(normalized)
                idx = lowered.find(phrase, idx + 1)

        # --- Phase 3: single-token extraction from remainder ---
        # Build a masked version of the lowered text where phrase spans are blanked.
        if phrase_spans:
            phrase_spans.sort()
            masked = list(lowered)
            for start, end in phrase_spans:
                for i in range(start, min(end, len(masked))):
                    masked[i] = " "
            masked_text = "".join(masked)
        else:
            masked_text = lowered

        for token in _TOKEN_RE.findall(masked_text):
            if token in _STOP_WORDS:
                continue
            normalized = _REQUIREMENT_ALIASES.get(token, token)
            requirements.add(normalized)

        return sorted(requirements)
