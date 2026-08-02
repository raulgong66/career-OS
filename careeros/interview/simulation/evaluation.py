"""Interview Simulation — answer evaluation engine (ADR-007, M1.17.4).

Deterministic analysis of interview answers per
``docs/platform-beta/interview-simulation/08-answer-evaluation-design.md``.

The engine owns answer analysis only:

- validating an ``InterviewAnswer`` against the question / session context
- checking coverage of the question intent and competencies
- validating evidence citations against ADR-002 canonical references
- validating claim alignment against ADR-003 canonical claim references
- analyzing answer structure using STAR / narrative conventions
- assessing measurability via the Core ``is_measurable`` service
- checking internal consistency and canonical alignment
- producing deterministic feedback signals and a session ``EvaluationSummary``

The engine explicitly does NOT own session lifecycle orchestration, question
generation or planning, canonical profile knowledge, AI correctness judgments,
persistence, transport, or profile mutation.  It is stateless: every method
receives its inputs explicitly and returns new objects, so the same inputs
always produce the same evaluation output.

Reference resolution to concrete profile entities is delegated to Core services
(e.g. the Resolution Engine); this engine validates the canonical ADR-002 shape
of references and never touches the canonical profile.
"""

from __future__ import annotations

import re
from typing import Any

from careeros.measurability import is_measurable
from careeros.reasoning import RuleRegistry

from ..domain import EvidenceCitation
from .domain import (
    AnswerEvaluation,
    EvaluationSummary,
    InterviewAnswer,
    InterviewFeedback,
    InterviewQuestionInstance,
    InterviewSession,
)
from .exceptions import (
    EvaluationPreconditionError,
    InvalidAnswerError,
    InvalidClaimError,
    InvalidQuestionError,
    MissingEvidenceReferenceError,
)

# Canonical rule ids for the evaluation pipeline stages.  Evaluation rules are
# defined and discovered through the shared Rule Registry (see the design
# document); a registry supplied to the engine must register these rules.
EVALUATION_RULE_IDS: tuple[str, ...] = (
    "evaluation.coverage",
    "evaluation.evidence",
    "evaluation.claim",
    "evaluation.star",
    "evaluation.measurability",
    "evaluation.consistency",
)

_STOPWORDS: frozenset[str] = frozenset(
    {
        "a", "an", "and", "are", "as", "at", "be", "been", "but", "by",
        "can", "could", "did", "do", "does", "for", "from", "has", "had",
        "have", "how", "i", "in", "into", "is", "it", "its", "of", "on",
        "or", "our", "so", "that", "the", "their", "then", "there", "these",
        "they", "this", "those", "to", "was", "we", "were", "what", "when",
        "where", "which", "who", "why", "will", "with", "would", "you", "your",
    }
)

# Canonical profile element kinds accepted as ADR-002 ``{id,type}`` references.
# Anything else (e.g. ``session``, ``plan``) is a session-owned fragment and is
# rejected as evidence.
_CANONICAL_ELEMENT_TYPES: frozenset[str] = frozenset(
    {
        "person",
        "experience",
        "skill",
        "project",
        "achievement",
        "certification",
        "education",
        "evidence",
        "claim",
    }
)

_STAR_MARKERS: dict[str, tuple[str, ...]] = {
    "situation": (
        "situation",
        "context",
        "background",
        "scenario",
        "challenge",
        "at the time",
    ),
    "task": (
        "task",
        "goal",
        "objective",
        "responsibility",
        "responsible",
        "tasked",
        "assigned",
        "asked to",
    ),
    "action": (
        "action",
        "implemented",
        "created",
        "built",
        "developed",
        "designed",
        "led",
        "launched",
        "introduced",
        "deployed",
        "migrated",
        "automated",
        "established",
        "organized",
    ),
    "result": (
        "result",
        "outcome",
        "achieved",
        "improved",
        "reduced",
        "increased",
        "saved",
        "delivered",
        "as a result",
        "ultimately",
        "this led to",
    ),
}

# Question categories that expect a full STAR response, a partial structured
# response, or a measurable outcome respectively.
_STRUCTURED_QUESTION_TYPES: frozenset[str] = frozenset(
    {"behavioral", "leadership", "project_deep_dive"}
)
_TECHNICAL_QUESTION_TYPES: frozenset[str] = frozenset(
    {"technical", "problem_solving"}
)
_MEASURABILITY_QUESTION_TYPES: frozenset[str] = frozenset(
    {"technical", "project_deep_dive", "problem_solving"}
)

# Antonym pairs used for deterministic internal-contradiction detection.
_CONTRADICTION_PAIRS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("increased", "grew"), ("decreased", "reduced", "fell")),
    (("successful", "succeeded"), ("failed", "failure")),
    (("always", "every"), ("never",)),
)

# ADR-002-style ``{type}:{id}`` references embedded in answer text.
_EVIDENCE_ID_PATTERN = re.compile(
    r"\b(experience|skill|project|achievement|education|certification|evidence|claim):"
    r"([a-z0-9_.-]+)\b",
    re.IGNORECASE,
)

_FEEDBACK_GUIDANCE: dict[str, str] = {
    "coverage": (
        "Address the question's intent directly and engage the question "
        "competencies."
    ),
    "evidence": (
        "Ground the answer in canonical profile evidence (ADR-002 {id,type} "
        "references)."
    ),
    "measurable outcome": (
        "Include a measurable outcome (metric, percentage, or business result)."
    ),
    "structure": (
        "Structure the answer around Situation, Task, Action, and Result."
    ),
    "consistency": (
        "Keep the answer internally consistent and aligned with canonical "
        "references."
    ),
}

_MISSING_ORDER: tuple[str, ...] = (
    "coverage",
    "evidence",
    "measurable outcome",
    "structure",
    "consistency",
)


def _significant_tokens(text: str) -> set[str]:
    """Lowercased alphanumeric tokens of length >= 3, minus stopwords."""
    tokens = re.findall(r"[a-z0-9]{3,}", text.lower())
    return {token for token in tokens if token not in _STOPWORDS}


def _word_in_text(word: str, text: str) -> bool:
    """``True`` when ``word`` appears at a word boundary in ``text``."""
    return bool(re.search(rf"\b{re.escape(word.lower())}\b", text.lower()))


def _citation_referenced_in_text(
    citation: EvidenceCitation, text: str
) -> bool:
    """``True`` when the answer text references a canonical citation.

    A citation is referenced when its quote appears verbatim (or as a word),
    or when its canonical ``element_id`` / ``element_type`` appear in the text.
    """
    quote = (citation.quote or "").strip()
    if quote:
        if " " in quote:
            if quote.lower() in text.lower():
                return True
        elif _word_in_text(quote, text):
            return True
    if citation.element_id and _word_in_text(citation.element_id, text):
        return True
    if citation.element_type and _word_in_text(citation.element_type, text):
        return True
    return False


def _intent_text(question: InterviewQuestionInstance) -> str:
    """The expected answer content for the question (text + suggested outline)."""
    parts = [question.question_text]
    suggested = question.suggested_answer
    if suggested is not None:
        parts.extend(
            part
            for part in (
                suggested.situation,
                suggested.task,
                suggested.action,
                suggested.result,
                suggested.achievement,
            )
            if part
        )
    return " ".join(parts)


def _claim_vocabulary(question: InterviewQuestionInstance) -> set[str]:
    """Canonical claim references for the question (ADR-003).

    The vocabulary is derived from the question's competency ids and its
    ``{id,type}`` context references — never ad hoc scoring criteria.
    """
    vocabulary: set[str] = set()
    for competency_id in question.competency_ids:
        vocabulary.update(_significant_tokens(competency_id))
    for ref in question.context_refs:
        vocabulary.update(_significant_tokens(str(ref.get("id", ""))))
        vocabulary.update(_significant_tokens(str(ref.get("type", ""))))
    return vocabulary


def _structure_applicable(category: str) -> bool:
    return category in _STRUCTURED_QUESTION_TYPES or category in _TECHNICAL_QUESTION_TYPES


def _follows_structure(
    question: InterviewQuestionInstance, text: str
) -> bool:
    """Qualitative STAR signal: does the answer follow a structured pattern?

    Behavioral / leadership / deep-dive questions require two STAR components;
    technical / problem-solving questions require one.  Career-motivation
    answers are not structure-checked.
    """
    category = question.category
    if category in _STRUCTURED_QUESTION_TYPES:
        required = 2
    elif category in _TECHNICAL_QUESTION_TYPES:
        required = 1
    else:
        return False
    matched = 0
    for markers in _STAR_MARKERS.values():
        if any(_word_in_text(marker, text) for marker in markers):
            matched += 1
    return matched >= required


def _consistency_findings(
    text: str,
    has_metric: bool,
    cites_evidence: bool,
    question: InterviewQuestionInstance,
) -> tuple[str, ...]:
    """Deterministic consistency signals for an answer.

    Detects internal contradictions, unsupported (un-evidenced) quantified
    claims, and mismatched evidence references relative to the question.
    """
    findings: list[str] = []

    for left, right in _CONTRADICTION_PAIRS:
        if any(_word_in_text(word, text) for word in left) and any(
            _word_in_text(word, text) for word in right
        ):
            findings.append("contradictory claims")
            break

    if has_metric and not cites_evidence:
        findings.append("unsupported claim")

    canonical_ids = {c.element_id for c in question.evidence_citations}
    for match in _EVIDENCE_ID_PATTERN.finditer(text):
        if match.group(2) not in canonical_ids:
            findings.append("mismatched evidence reference")
            break

    return tuple(findings)


class EvaluationEngine:
    """Deterministic answer analysis (ADR-007, M1.17.4).

    Stateless by design: inputs are passed explicitly and new objects are
    returned, so the same answer/question/session always produce the same
    evaluation output.  The engine never mutates the session, the answer, or
    the canonical profile.
    """

    def evaluate_answer(
        self,
        answer: InterviewAnswer,
        question: InterviewQuestionInstance | None = None,
        session: InterviewSession | None = None,
        registry: RuleRegistry | None = None,
    ) -> AnswerEvaluation:
        """Run the full evaluation pipeline over a single answer.

        The pipeline stages — Coverage Check, Evidence Validation, Claim
        Validation, STAR Analysis, Measurability Analysis, and Consistency
        Analysis — are applied deterministically and folded into an
        ``AnswerEvaluation`` signal vector.
        """
        self._validate_answer(answer)
        text = answer.text.strip()
        if session is not None and answer.session_id != session.id:
            raise InvalidAnswerError(
                f"Answer for session '{answer.session_id}' does not belong to "
                f"session '{session.id}'."
            )
        question = self._resolve_question(answer, question, session)
        self._require_registry_rules(registry)
        self._validate_claim_metadata(question)
        self._validate_evidence(question, text, answer, session)

        citations = self._referenced_citations(question, text)
        return AnswerEvaluation(
            covers_claim=self._covers_claim(question, text),
            has_metric=is_measurable(text),
            cites_evidence=bool(citations),
            follows_structure=_follows_structure(question, text),
            matches_question_competencies=self._matches_competencies(question, text),
            citations=citations,
        )

    def build_feedback(
        self,
        answer: InterviewAnswer,
        question: InterviewQuestionInstance | None = None,
        session: InterviewSession | None = None,
        evaluation: AnswerEvaluation | None = None,
        registry: RuleRegistry | None = None,
    ) -> InterviewFeedback:
        """Derive advisory feedback items from an answer's evaluation.

        The feedback is advisory (not final narrative): it lists the missing
        evaluation dimensions and a deterministic improvement recommendation
        for a future AI enrichment layer to frame.
        """
        self._validate_answer(answer)
        text = answer.text.strip()
        if session is not None and answer.session_id != session.id:
            raise InvalidAnswerError(
                f"Answer for session '{answer.session_id}' does not belong to "
                f"session '{session.id}'."
            )
        question = self._resolve_question(answer, question, session)
        self._require_registry_rules(registry)
        if evaluation is None:
            evaluation = self.evaluate_answer(answer, question, session, registry)

        findings = _consistency_findings(
            text, evaluation.has_metric, evaluation.cites_evidence, question
        )
        missing = self._missing_signals(question, evaluation, findings)
        return InterviewFeedback(
            id=f"{answer.id}:feedback",
            question_id=answer.question_id,
            answer_id=answer.id,
            missing=missing,
            improvement_recommendation=self._improvement_recommendation(missing),
            citations=evaluation.citations,
        )

    def evaluate_session(
        self,
        session: InterviewSession,
        registry: RuleRegistry | None = None,
    ) -> EvaluationSummary:
        """Aggregate the evaluations of a session's answers.

        Answers that already carry an ``AnswerEvaluation`` are reused;
        the rest are evaluated deterministically.  Counts mirror the design's
        evaluation dimensions (coverage, evidence, claim alignment,
        measurability) plus qualitative structure and consistency signals.
        """
        if not isinstance(session, InterviewSession):
            raise EvaluationPreconditionError(
                "Cannot evaluate a non-InterviewSession "
                f"(got {type(session).__name__})."
            )
        self._require_registry_rules(registry)

        coverage = evidence = alignment = measurability = structure = 0
        inconsistent = 0
        for answer in session.answers:
            question = self._resolve_question(answer, None, session)
            evaluation = answer.evaluation
            if evaluation is None:
                evaluation = self.evaluate_answer(answer, question, session, registry)
            text = answer.text.strip()
            findings = _consistency_findings(
                text, evaluation.has_metric, evaluation.cites_evidence, question
            )
            if evaluation.covers_claim:
                coverage += 1
            if evaluation.cites_evidence:
                evidence += 1
            if evaluation.matches_question_competencies:
                alignment += 1
            if evaluation.has_metric:
                measurability += 1
            if evaluation.follows_structure:
                structure += 1
            if findings:
                inconsistent += 1

        return EvaluationSummary(
            total_answers=session.answer_count,
            coverage=coverage,
            evidence=evidence,
            claim_alignment=alignment,
            measurability=measurability,
            structure=structure,
            inconsistent_answers=inconsistent,
        )

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _validate_answer(answer: InterviewAnswer) -> None:
        if not isinstance(answer, InterviewAnswer):
            raise InvalidAnswerError(
                f"Cannot evaluate a non-InterviewAnswer ({type(answer).__name__})."
            )
        if not answer.text or not answer.text.strip():
            raise InvalidAnswerError("Cannot evaluate an empty answer.")

    @staticmethod
    def _resolve_question(
        answer: InterviewAnswer,
        question: InterviewQuestionInstance | None,
        session: InterviewSession | None,
    ) -> InterviewQuestionInstance:
        if question is None:
            if session is None:
                raise InvalidQuestionError(
                    f"Answer '{answer.id}' has no question context and no "
                    "session to resolve it from."
                )
            for candidate in session.questions:
                if candidate.id == answer.question_id:
                    return candidate
            raise InvalidQuestionError(
                f"Answer '{answer.id}' targets question '{answer.question_id}' "
                f"which is not part of session '{session.id}'."
            )
        if question.id != answer.question_id:
            raise InvalidQuestionError(
                f"Answer '{answer.id}' targets question '{answer.question_id}' "
                f"but the supplied question is '{question.id}'."
            )
        if session is not None and question.session_id != session.id:
            raise InvalidQuestionError(
                f"Question '{question.id}' belongs to session "
                f"'{question.session_id}' not session '{session.id}'."
            )
        return question

    @staticmethod
    def _require_registry_rules(registry: RuleRegistry | None) -> None:
        if registry is None:
            return
        if not isinstance(registry, RuleRegistry):
            raise EvaluationPreconditionError(
                "The evaluation rule set must be a RuleRegistry "
                f"(got {type(registry).__name__})."
            )
        missing = [rid for rid in EVALUATION_RULE_IDS if registry.get(rid) is None]
        if missing:
            raise EvaluationPreconditionError(
                "The supplied rule registry is missing required evaluation "
                f"rules: {', '.join(missing)}."
            )

    @staticmethod
    def _validate_claim_metadata(question: InterviewQuestionInstance) -> None:
        for ref in question.context_refs:
            if not isinstance(ref, dict):
                raise InvalidClaimError(
                    f"Question '{question.id}' has a non-dict context reference."
                )
            if not str(ref.get("id", "") or "").strip():
                raise InvalidClaimError(
                    f"Question '{question.id}' has a context reference without "
                    "an 'id' (ADR-003 claim metadata missing)."
                )
            if not str(ref.get("type", "") or "").strip():
                raise InvalidClaimError(
                    f"Question '{question.id}' has a context reference without "
                    "a 'type' (ADR-003 claim metadata missing)."
                )
        for competency_id in question.competency_ids:
            if not str(competency_id or "").strip():
                raise InvalidClaimError(
                    f"Question '{question.id}' has an empty competency "
                    "reference (ADR-003 claim metadata missing)."
                )

    @staticmethod
    def _validate_evidence(
        question: InterviewQuestionInstance,
        text: str,
        answer: InterviewAnswer,
        session: InterviewSession | None,
    ) -> None:
        for citation in question.evidence_citations:
            if not isinstance(citation, EvidenceCitation):
                raise MissingEvidenceReferenceError(
                    f"Question '{question.id}' carries a non-canonical "
                    "evidence citation (expected ADR-002 {id,type})."
                )
            element_id = (citation.element_id or "").strip()
            element_type = (citation.element_type or "").strip()
            if not element_id or not element_type:
                raise MissingEvidenceReferenceError(
                    f"Evidence citation on question '{question.id}' is "
                    "malformed: ADR-002 requires both id and type."
                )
            if element_type not in _CANONICAL_ELEMENT_TYPES:
                raise MissingEvidenceReferenceError(
                    f"Evidence citation '{element_type}:{element_id}' is not a "
                    "canonical profile reference (ADR-002); session-owned "
                    "fragments cannot be cited as evidence."
                )
        if answer.question_id and answer.question_id in text:
            raise MissingEvidenceReferenceError(
                f"Answer '{answer.id}' cites the session-owned question "
                f"reference '{answer.question_id}' as evidence; canonical "
                "references (ADR-002 {id,type}) must point at profile entities."
            )
        if session is not None and session.plan_ref and session.plan_ref in text:
            raise MissingEvidenceReferenceError(
                f"Answer '{answer.id}' cites the session plan reference as "
                "evidence; canonical references (ADR-002 {id,type}) must point "
                "at profile entities."
            )

    @staticmethod
    def _referenced_citations(
        question: InterviewQuestionInstance, text: str
    ) -> tuple[EvidenceCitation, ...]:
        return tuple(
            citation
            for citation in question.evidence_citations
            if _citation_referenced_in_text(citation, text)
        )

    @staticmethod
    def _covers_claim(
        question: InterviewQuestionInstance, text: str
    ) -> bool:
        intent = _significant_tokens(_intent_text(question))
        if not intent:
            return False
        return bool(_significant_tokens(text) & intent)

    @staticmethod
    def _matches_competencies(
        question: InterviewQuestionInstance, text: str
    ) -> bool:
        vocabulary = _claim_vocabulary(question)
        if not vocabulary:
            return False
        return bool(_significant_tokens(text) & vocabulary)

    @staticmethod
    def _missing_signals(
        question: InterviewQuestionInstance,
        evaluation: AnswerEvaluation,
        findings: tuple[str, ...],
    ) -> tuple[str, ...]:
        signals: set[str] = set()
        if not evaluation.covers_claim:
            signals.add("coverage")
        if not evaluation.cites_evidence:
            signals.add("evidence")
        if (
            question.category in _MEASURABILITY_QUESTION_TYPES
            and not evaluation.has_metric
        ):
            signals.add("measurable outcome")
        if _structure_applicable(question.category) and not evaluation.follows_structure:
            signals.add("structure")
        for finding in findings:
            if finding == "contradictory claims":
                signals.add("consistency")
            elif finding in ("unsupported claim", "mismatched evidence reference"):
                signals.add("evidence")
        return tuple(signal for signal in _MISSING_ORDER if signal in signals)

    @staticmethod
    def _improvement_recommendation(missing: tuple[str, ...]) -> str | None:
        if not missing:
            return None
        return " ".join(_FEEDBACK_GUIDANCE[signal] for signal in missing)
