"""DTO mapping for the Interview Simulation API (M1.19).

Composes transport-safe payloads from Interview Simulation domain models. The
API layer stays transport-only: it never implements evaluation, report
assembly, or profile logic. Evidence references are preserved as ADR-002
``{id, type}`` links and profile-derived content is not duplicated into session
state (M1.19 vertical slice spec).
"""

from __future__ import annotations

from typing import Any

from careeros.interview.domain import InterviewQuestion
from careeros.interview.simulation import InterviewSession


def to_question_response(question: InterviewQuestion) -> dict[str, Any]:
    """Curate a transport-safe question DTO.

    Evidence citations are projected to their ``{id, type}`` reference form and
    profile-derived outline content is omitted from session payloads.
    """
    return {
        "id": question.id,
        "category": question.category.value,
        "text": question.text,
        "competency_ids": list(question.competency_ids),
        "context_refs": [dict(ref) for ref in question.context_refs],
        "evidence_citations": [
            citation.source_ref() for citation in question.evidence_citations
        ],
        "difficulty": question.difficulty,
    }


def to_session_response(session: InterviewSession) -> dict[str, Any]:
    """Map an ``InterviewSession`` to its transport DTO."""
    current = session.current_question_instance()
    current_question = None
    if current is not None:
        current_question = {
            "index": current.index,
            "total": current.total,
            "question": to_question_response(current.question),
        }
    return {
        "session_id": session.session_id,
        "profile_id": session.plan.person_id,
        "state": session.state.value,
        "current_question_index": session.current_question_index,
        "question_count": session.question_count,
        "answered_count": session.answered_count,
        "current_question": current_question,
        "answers": [answer.to_dict() for answer in session.answers],
        "metadata": dict(session.metadata),
    }
