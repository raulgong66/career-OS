"""Provider-neutral Transformation Interpreter.

Turns a client business objective into a structured Transformation Plan
containing 3-5 phases, each wrapping a canonical MissionContract. The
transformation is a *composition of Missions*, not a replacement for them.

The provider proposes only the transformation structure (phases, sequencing,
roles, requirements, capabilities, constraints, narrative). Every phase's
MissionContract is deterministically built through ``build_contract()`` so
the existing Mission evaluation pipeline consumes it unchanged.

The provider never produces candidate evidence, evidence strength,
confidence, provenance, qualification, or scores.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Iterable

from careeros.ai import AIError, create_ai_provider

from .contract import (
    MissionContract,
    MissionContractError,
    build_contract,
)

if TYPE_CHECKING:
    from careeros.ai import AIProvider

TRANSFORMATION_TEMPERATURE = 0.1
TRANSFORMATION_TIMEOUT = 90.0
TRANSFORMATION_MAX_TOKENS = 4000

_MIN_PHASES = 3
_MAX_PHASES = 5
_MAX_SUMMARY_LENGTH = 800
_MAX_PHASE_TITLE_LENGTH = 120
_MAX_PHASE_DESCRIPTION_LENGTH = 1500
_MAX_CONSTRAINT_LENGTH = 300
_MAX_CONSTRAINT_LIST_LENGTH = 25

_SYSTEM_INSTRUCTION = (
    "You are the CareerOS Transformation Interpreter.\n"
    "\n"
    "You interpret a client business objective and propose a structured "
    "Transformation Plan composed of 3-5 sequential phases.\n"
    "\n"
    "Each phase must describe a concrete, independently evaluable mission.\n"
    "\n"
    "Rules:\n"
    "- Propose phases, roles, requirements, capabilities, evidence standards, "
    "and constraints ONLY. Never invent candidate evidence, experience, "
    "certifications, projects, or capabilities of any person.\n"
    "- Do not assign evidence strength, confidence, provenance, qualification, "
    "or scores.\n"
    "- requirements must be short, concrete capability statements "
    "(e.g. \"real production AWS migration experience\", \"DevSecOps\", "
    "\"GDPR compliance\").\n"
    "- Every list may be empty except requirements, which must have at least "
    "one item per phase.\n"
    "- Return strict JSON only with exactly these fields:\n"
    "  {\"summary\": string, \"constraints\": [string, ...], \"phases\": [\n"
    "    {\"phase_number\": int, \"title\": string, \"description\": string, "
    "\"role\": string, \"requirements\": [string, ...], \"capabilities\": "
    "[string, ...], \"evidence_standards\": [string, ...], "
    "\"constraints\": [string, ...]}, ...\n"
    "  ]}\n"
    "- summary: one sentence summarizing the overall transformation.\n"
    "- phases: exactly 3 to 5 phases, each with phase_number starting at 1.\n"
    "- Each phase must have at least one requirement.\n"
)

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class TransformationInterpretationError(Exception):
    """Raised when a transformation cannot be interpreted into a valid plan."""


class TruncatedTransformationResponseError(TransformationInterpretationError):
    """Raised when the provider's JSON response is cut off before completion."""


class PhaseCountError(TransformationInterpretationError):
    """Raised when the plan has fewer than 3 or more than 5 phases."""


class PhaseContractError(TransformationInterpretationError):
    """Raised when a phase cannot be built into a valid MissionContract."""


def _plan_id(objective: str) -> str:
    """Deterministic identity for a transformation plan."""
    digest = hashlib.sha256(objective.strip().encode("utf-8")).hexdigest()
    return digest[:16]


def _phase_id(plan_id: str, phase_number: int, title: str) -> str:
    """Deterministic identity for a transformation phase."""
    payload = f"{plan_id}:{phase_number}:{title.strip()}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return digest[:12]


def build_prompt(objective: str) -> str:
    """Build the exact prompt sent to the provider."""
    payload = {"objective": objective.strip()}
    return _SYSTEM_INSTRUCTION + "\n\n" + json.dumps(payload, ensure_ascii=False, indent=2)


def _is_truncated(text: str) -> bool:
    """True when the response clearly ends before the JSON object completes."""
    opens = 0
    for ch in text:
        if ch == "{":
            opens += 1
        elif ch == "}":
            opens -= 1
    return opens > 0


def _parse_json(raw: str) -> Any:
    text = raw.strip()
    if not text:
        return None
    fence = _FENCE_RE.search(text)
    if fence:
        text = fence.group(1).strip()
    if not text:
        return None
    if _is_truncated(text):
        raise TruncatedTransformationResponseError(
            "The transformation response was truncated."
        )
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _clean_string(value: Any, max_length: int) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or len(text) > max_length:
        return None
    return text


def parse_response(raw: str, objective: str) -> TransformationPlan | None:
    """Deterministically validate and canonicalize the provider's response.

    Returns ``None`` when the response is not a valid plan payload.
    Raises :class:`TruncatedTransformationResponseError` when the JSON is
    cut off.
    """
    data = _parse_json(raw)
    if data is None or not isinstance(data, dict):
        return None

    summary = _clean_string(data.get("summary"), _MAX_SUMMARY_LENGTH)
    if summary is None:
        return None

    raw_phases = data.get("phases")
    if not isinstance(raw_phases, list):
        return None

    if len(raw_phases) < _MIN_PHASES or len(raw_phases) > _MAX_PHASES:
        return None

    global_constraints = _as_string_list(data.get("constraints"))

    objective_id = _plan_id(objective)

    phases: list[TransformationPhase] = []
    for raw_phase in raw_phases:
        if not isinstance(raw_phase, dict):
            return None

        phase_number = raw_phase.get("phase_number")
        if not isinstance(phase_number, int) or phase_number < 1:
            return None

        title = _clean_string(raw_phase.get("title"), _MAX_PHASE_TITLE_LENGTH)
        if title is None:
            return None

        description = _clean_string(
            raw_phase.get("description"), _MAX_PHASE_DESCRIPTION_LENGTH
        )
        if description is None:
            return None

        role = raw_phase.get("role")
        if not isinstance(role, str) or not role.strip():
            return None
        role = role.strip()

        requirements = _as_string_list(raw_phase.get("requirements"))
        capabilities = _as_string_list(raw_phase.get("capabilities"))
        evidence_standards = _as_string_list(raw_phase.get("evidence_standards"))
        phase_constraints = _as_string_list(raw_phase.get("constraints"))

        try:
            contract = build_contract(
                mission_statement=description,
                summary=description[:_MAX_SUMMARY_LENGTH],
                role=role,
                requirements=requirements,
                capabilities=capabilities,
                evidence_standards=evidence_standards,
                constraints=phase_constraints,
            )
        except MissionContractError:
            return None

        phase_id = _phase_id(objective_id, phase_number, title)
        phases.append(
            TransformationPhase(
                phase_id=phase_id,
                phase_number=phase_number,
                title=title,
                description=description,
                contract=contract,
            )
        )

    # Validate phase numbers are sequential
    sorted_phases = sorted(phases, key=lambda p: p.phase_number)
    for idx, phase in enumerate(sorted_phases, start=1):
        if phase.phase_number != idx:
            return None

    return TransformationPlan(
        plan_id=objective_id,
        objective=objective.strip(),
        summary=summary,
        phases=tuple(sorted_phases),
        constraints=tuple(global_constraints[:_MAX_CONSTRAINT_LIST_LENGTH]),
    )


@dataclass(frozen=True)
class TransformationPhase:
    """A single phase of a Transformation Plan.

    Each phase contains a fully valid, canonical MissionContract that can be
    consumed by the existing Mission evaluation pipeline unchanged.
    """

    phase_id: str
    phase_number: int
    title: str
    description: str
    contract: MissionContract

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase_id": self.phase_id,
            "phase_number": self.phase_number,
            "title": self.title,
            "description": self.description,
            "contract": self.contract.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Any) -> "TransformationPhase":
        if not isinstance(data, dict):
            raise MissionContractError("Transformation phase must be an object.")
        try:
            phase_id = data.get("phase_id", "")
            phase_number = data.get("phase_number")
            title = data.get("title", "")
            description = data.get("description", "")
            contract = MissionContract.from_dict(data.get("contract", {}))
        except (MissionContractError, AttributeError, TypeError) as exc:
            raise MissionContractError(f"Invalid transformation phase: {exc}") from exc
        if not isinstance(phase_number, int) or phase_number < 1:
            raise MissionContractError("Phase number must be a positive integer.")
        if not isinstance(phase_id, str) or not phase_id.strip():
            raise MissionContractError("Phase ID must be a non-empty string.")
        return cls(
            phase_id=phase_id.strip(),
            phase_number=phase_number,
            title=title.strip(),
            description=description.strip(),
            contract=contract,
        )


@dataclass(frozen=True)
class TransformationPlan:
    """Structured representation of a multi-phase transformation.

    Contains 3-5 TransformationPhase objects, each wrapping a canonical
    MissionContract. The plan is provider-proposed and deterministically
    canonicalized.
    """

    plan_id: str
    objective: str
    summary: str
    phases: tuple[TransformationPhase, ...] = field(default_factory=tuple)
    constraints: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "objective": self.objective,
            "summary": self.summary,
            "phases": [phase.to_dict() for phase in self.phases],
            "constraints": list(self.constraints),
        }

    @classmethod
    def from_dict(cls, data: Any) -> "TransformationPlan":
        if not isinstance(data, dict):
            raise MissionContractError("Transformation plan must be an object.")
        try:
            plan_id = data.get("plan_id", "")
            objective = data.get("objective", "")
            summary = data.get("summary", "")
            raw_phases = data.get("phases", [])
            constraints = data.get("constraints", [])
        except (TypeError, ValueError) as exc:
            raise MissionContractError(f"Invalid transformation plan: {exc}") from exc
        if not isinstance(plan_id, str) or not plan_id.strip():
            raise MissionContractError("Plan ID must be a non-empty string.")
        if not isinstance(objective, str) or not objective.strip():
            raise MissionContractError("Objective must be a non-empty string.")
        phases = tuple(TransformationPhase.from_dict(p) for p in raw_phases)
        return cls(
            plan_id=plan_id.strip(),
            objective=objective.strip(),
            summary=summary.strip() if isinstance(summary, str) else "",
            phases=phases,
            constraints=tuple(
                c for c in constraints if isinstance(c, str) and c.strip()
            ),
        )


class TransformationInterpreter:
    """Interprets a client objective through an ``AIProvider``.

    ``provider`` is optional and resolved lazily through
    ``create_ai_provider()`` so the interpreter stays provider-neutral.
    Tests inject a ``MockAIProvider``.
    """

    def __init__(self, provider: "AIProvider | None" = None) -> None:
        self.provider = provider

    def _resolve_provider(self) -> "AIProvider":
        if self.provider is None:
            self.provider = create_ai_provider()
        return self.provider

    def interpret(self, objective: str) -> TransformationPlan:
        """Interpret a client business objective into a Transformation Plan.

        Raises:
            TransformationInterpretationError: When the provider fails or the
                response cannot be validated into a plan.
        """
        if not objective or not objective.strip():
            raise TransformationInterpretationError("Objective text is empty.")
        prompt = build_prompt(objective)
        try:
            raw = self._resolve_provider().generate(
                prompt,
                temperature=TRANSFORMATION_TEMPERATURE,
                timeout=TRANSFORMATION_TIMEOUT,
                max_tokens=TRANSFORMATION_MAX_TOKENS,
                json_mode=True,
            )
        except AIError as exc:
            raise TransformationInterpretationError(
                f"Transformation interpretation failed: {exc}"
            ) from exc
        try:
            plan = parse_response(raw, objective)
        except TruncatedTransformationResponseError as exc:
            raise TransformationInterpretationError(str(exc)) from exc
        if plan is None:
            raise TransformationInterpretationError(
                "The interpreter returned an invalid transformation plan."
            )
        return plan
