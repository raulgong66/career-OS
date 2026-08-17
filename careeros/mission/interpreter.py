"""Provider-neutral Mission Interpreter.

Turns a natural-language business mission into a structured Mission Contract.
The interpreter depends only on the ``AIProvider`` abstraction
(``careeros.ai``); prompt construction and response parsing are business logic
that live here, mirroring the synthesis layer (``careeros.csks.synthesis``)
and acquisition extraction (``careeros.acquisition.llm_extractor``).

The provider proposes; the deterministic layer
(``careeros.mission.contract``) canonicalizes. The provider never produces
candidate evidence, evidence strength, confidence, provenance, qualification,
or scores.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from careeros.ai import AIError, create_ai_provider

from .contract import MissionContract, MissionContractError, build_contract

if TYPE_CHECKING:
    from careeros.ai import AIProvider

MISSION_INTERPRET_TEMPERATURE = 0.1
MISSION_INTERPRET_TIMEOUT = 60.0
MISSION_INTERPRET_MAX_TOKENS = 2000

_SYSTEM_INSTRUCTION = (
    "You are the CareerOS Mission Interpreter.\n"
    "\n"
    "You interpret a business mission expressed in natural language and propose "
    "a structured Mission Contract used to evaluate candidate evidence.\n"
    "\n"
    "Rules:\n"
    "- Propose structured requirements and capabilities ONLY. Never invent candidate "
    "evidence, experience, certifications, projects, or capabilities of any person.\n"
    "- Do not assign evidence strength, confidence, provenance, qualification, or scores.\n"
    "- requirements must be short, concrete capability statements "
    "(e.g. \"real production AWS migration experience\", \"DevSecOps\", \"GDPR compliance\").\n"
    "- Return strict JSON only with exactly these fields: "
    "{\"summary\": string, \"role\": string, \"requirements\": [string, ...], "
    "\"capabilities\": [string, ...], \"evidence_standards\": [string, ...], "
    "\"constraints\": [string, ...]}.\n"
    "- summary: one sentence restating the mission.\n"
    "- role: the primary required role or capability for the mission.\n"
    "- capabilities: the capabilities the team must have.\n"
    "- evidence_standards: what counts as real evidence for this mission.\n"
    "- constraints: non-negotiable constraints (compliance, resilience, etc.).\n"
    "- Every list may be empty except requirements, which must have at least one item.\n"
)

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class MissionInterpretationError(Exception):
    """Raised when a mission cannot be interpreted into a valid contract."""


class TruncatedMissionResponseError(MissionInterpretationError):
    """Raised when the provider's JSON response is cut off before completion."""


def build_prompt(mission: str) -> str:
    """Build the exact prompt sent to the provider.

    The provider receives only the mission text; nothing else is serialized.
    """
    payload = {"mission": mission.strip()}
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
        raise TruncatedMissionResponseError("The interpreter response was truncated.")
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


_LIST_FIELDS = ("requirements", "capabilities", "evidence_standards", "constraints")


def parse_response(raw: str, mission: str) -> MissionContract | None:
    """Deterministically validate and canonicalize the provider's response.

    Returns ``None`` when the response is not a valid contract payload;
    raises :class:`TruncatedMissionResponseError` when the JSON is cut off.
    """
    data = _parse_json(raw)
    if data is None or not isinstance(data, dict):
        return None
    for field in _LIST_FIELDS:
        value = data.get(field)
        if value is not None and not isinstance(value, list):
            return None
    try:
        return build_contract(
            mission_statement=mission,
            summary=data.get("summary"),
            role=data.get("role"),
            requirements=_as_string_list(data.get("requirements")),
            capabilities=_as_string_list(data.get("capabilities")),
            evidence_standards=_as_string_list(data.get("evidence_standards")),
            constraints=_as_string_list(data.get("constraints")),
        )
    except MissionContractError:
        return None


class MissionInterpreter:
    """Interprets a mission through an ``AIProvider``.

    ``provider`` is optional and resolved lazily through
    ``create_ai_provider()`` (the ``LLM_PROVIDER`` environment selects the
    implementation) so the interpreter stays provider-neutral. Tests inject
    a ``MockAIProvider``.
    """

    def __init__(self, provider: "AIProvider | None" = None) -> None:
        self.provider = provider

    def _resolve_provider(self) -> "AIProvider":
        if self.provider is None:
            self.provider = create_ai_provider()
        return self.provider

    def interpret(self, mission: str) -> MissionContract:
        """Interpret a natural-language mission into a Mission Contract.

        Raises:
            MissionInterpretationError: When the provider fails or the
                response cannot be validated into a contract.
        """
        if not mission or not mission.strip():
            raise MissionInterpretationError("Mission text is empty.")
        prompt = build_prompt(mission)
        try:
            raw = self._resolve_provider().generate(
                prompt,
                temperature=MISSION_INTERPRET_TEMPERATURE,
                timeout=MISSION_INTERPRET_TIMEOUT,
                max_tokens=MISSION_INTERPRET_MAX_TOKENS,
                json_mode=True,
            )
        except AIError as exc:
            raise MissionInterpretationError(f"Mission interpretation failed: {exc}") from exc
        try:
            contract = parse_response(raw, mission)
        except TruncatedMissionResponseError as exc:
            raise MissionInterpretationError(str(exc)) from exc
        if contract is None:
            raise MissionInterpretationError("The interpreter returned an invalid mission contract.")
        return contract
