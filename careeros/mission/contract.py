"""Mission Contract domain model and deterministic normalization.

The Mission Contract is the structured representation of a business mission
that the provider-neutral Mission Interpreter produces. It is validated and
canonicalized deterministically against the existing optimizer requirement
model (``careeros.optimizer``): the LLM proposes, the engine canonicalizes.

The contract is designed to become a persistent CareerOS object later without
redesign: ``mission_id`` is a deterministic digest of the mission statement
and every field is a plain serializable value with a lossless
``to_dict``/``from_dict`` round trip. No persistence is implemented in this
MVP.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Iterable

from ..optimizer import CVOptimizer

_MAX_SUMMARY_LENGTH = 500
_MAX_ROLE_LENGTH = 120
_MAX_LIST_ITEM_LENGTH = 200
_MAX_LIST_LENGTH = 25


class MissionContractError(ValueError):
    """Raised when a mission contract is invalid or non-canonical."""


def _mission_id(mission_statement: str) -> str:
    """Deterministic identity for a mission (future persistence key)."""
    digest = hashlib.sha256(mission_statement.strip().encode("utf-8")).hexdigest()
    return digest[:16]


def normalize_requirements(*texts: str) -> list[str]:
    """Canonicalize requirement candidates through the optimizer pipeline.

    Every candidate string (the mission statement plus the interpreter's
    proposed requirements) is run through the existing deterministic
    requirement-extraction heuristic (``CVOptimizer.extract_requirements``)
    so the contract speaks exactly the engine's vocabulary: aliases are
    canonicalized (AWS → amazon web services) and filler words are removed.
    """
    extracted: set[str] = set()
    for text in texts:
        if not text or not text.strip():
            continue
        extracted.update(CVOptimizer.extract_requirements(text))
    return sorted(extracted)


def resolve_concepts(requirements: Iterable[str]) -> list[str]:
    """Resolve normalized requirement strings to canonical concept IDs.

    Reuses the optimizer's alias-based concept index unchanged.
    """
    return sorted(CVOptimizer._resolve_concepts(list(requirements)))


def _clean_list(items: Iterable[Any] | None) -> tuple[str, ...]:
    """Keep bounded, non-empty, deduplicated string entries in order."""
    cleaned: list[str] = []
    for item in items or []:
        if not isinstance(item, str):
            continue
        text = item.strip()
        if text and len(text) <= _MAX_LIST_ITEM_LENGTH and text not in cleaned:
            cleaned.append(text)
    return tuple(cleaned)


@dataclass(frozen=True)
class MissionContract:
    """Structured, deterministic representation of a business mission.

    ``requirements`` and ``concepts`` are always produced by the deterministic
    normalization layer, never taken verbatim from the interpreter.
    """

    mission_id: str
    mission_statement: str
    summary: str
    role: str
    requirements: tuple[str, ...]
    concepts: tuple[str, ...]
    capabilities: tuple[str, ...]
    evidence_standards: tuple[str, ...]
    constraints: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain, persistable payload."""
        return {
            "mission_id": self.mission_id,
            "mission_statement": self.mission_statement,
            "summary": self.summary,
            "role": self.role,
            "requirements": list(self.requirements),
            "concepts": list(self.concepts),
            "capabilities": list(self.capabilities),
            "evidence_standards": list(self.evidence_standards),
            "constraints": list(self.constraints),
        }

    @classmethod
    def from_dict(cls, data: Any) -> "MissionContract":
        """Rebuild a contract from a serialized payload with integrity checks.

        The deterministic identity must match the mission statement and every
        list field must contain only strings.
        """
        if not isinstance(data, dict):
            raise MissionContractError("Mission contract must be an object.")
        try:
            contract = cls(
                mission_id=_required_string(data, "mission_id"),
                mission_statement=_required_string(data, "mission_statement"),
                summary=_required_string(data, "summary"),
                role=_required_string(data, "role"),
                requirements=_string_list(data, "requirements"),
                concepts=_string_list(data, "concepts"),
                capabilities=_string_list(data, "capabilities"),
                evidence_standards=_string_list(data, "evidence_standards"),
                constraints=_string_list(data, "constraints"),
            )
        except MissionContractError:
            raise
        except (TypeError, ValueError) as exc:
            raise MissionContractError(f"Invalid mission contract: {exc}") from exc
        if contract.mission_id != _mission_id(contract.mission_statement):
            raise MissionContractError("Mission contract integrity check failed.")
        return contract


def _required_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise MissionContractError(f"Mission contract field '{key}' must be a non-empty string.")
    return value.strip()


def _string_list(data: dict[str, Any], key: str) -> tuple[str, ...]:
    value = data.get(key)
    if not isinstance(value, (list, tuple)):
        raise MissionContractError(f"Mission contract field '{key}' must be a list.")
    entries: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise MissionContractError(f"Mission contract field '{key}' must contain only strings.")
        cleaned = item.strip()
        if cleaned:
            entries.append(cleaned)
    return tuple(entries)


def build_contract(
    mission_statement: str,
    summary: str,
    role: str,
    requirements: Iterable[str],
    capabilities: Iterable[Any] | None = None,
    evidence_standards: Iterable[Any] | None = None,
    constraints: Iterable[Any] | None = None,
) -> MissionContract:
    """Deterministically build and canonicalize a Mission Contract.

    ``requirements`` are the interpreter's proposals; they are canonicalized
    through the optimizer requirement pipeline together with the mission
    statement, and resolved to canonical concepts. No interpreter-supplied
    value is trusted without passing this deterministic layer.
    """
    if not isinstance(mission_statement, str) or not mission_statement.strip():
        raise MissionContractError("Mission statement is required.")
    mission = mission_statement.strip()

    if not isinstance(summary, str) or not summary.strip():
        raise MissionContractError("Mission contract summary is missing or too long.")
    summary = summary.strip()
    if len(summary) > _MAX_SUMMARY_LENGTH:
        raise MissionContractError("Mission contract summary is missing or too long.")

    if not isinstance(role, str) or not role.strip():
        raise MissionContractError("Mission contract role is missing or too long.")
    role = role.strip()
    if len(role) > _MAX_ROLE_LENGTH:
        raise MissionContractError("Mission contract role is missing or too long.")

    try:
        proposals = list(requirements or [])
    except TypeError as exc:
        raise MissionContractError("Mission contract requirements must be strings.") from exc
    if any(not isinstance(item, str) for item in proposals):
        raise MissionContractError("Mission contract requirements must be strings.")
    if len(proposals) > _MAX_LIST_LENGTH:
        raise MissionContractError("Mission contract has too many requirements.")

    reqs = normalize_requirements(mission, *proposals)
    # Keep only requirements the engine can actually match: a requirement that
    # resolves to no canonical concept is noise to the optimizer. This filter
    # uses the existing deterministic concept index and keeps the contract
    # aligned with the engine's vocabulary.
    reqs = sorted(
        requirement
        for requirement in reqs
        if CVOptimizer._resolve_concepts([requirement])
    )
    if not reqs:
        raise MissionContractError("Mission contract must resolve to at least one requirement.")

    return MissionContract(
        mission_id=_mission_id(mission),
        mission_statement=mission,
        summary=summary,
        role=role,
        requirements=tuple(reqs),
        concepts=tuple(resolve_concepts(reqs)),
        capabilities=_clean_list(capabilities),
        evidence_standards=_clean_list(evidence_standards),
        constraints=_clean_list(constraints),
    )
