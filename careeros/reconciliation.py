"""Deterministic profile reconciliation for CareerOS Phase 3A.

Compares two existing profiles and produces a reconciliation plan classifying
differences without modifying either profile.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Sequence

from .import_classification import _compare_identity, _person_signals
from .profile_repository import ProfileRecord, ProfileRepository


class EntityDiffType(str, Enum):
    """Classification of how an entity differs between two profiles."""
    SAME = "SAME"
    CONFLICT = "CONFLICT"
    ONLY_IN_LEFT = "ONLY_IN_LEFT"
    ONLY_IN_RIGHT = "ONLY_IN_RIGHT"


class ProvenanceWarningType(str, Enum):
    """Types of provenance warnings that can be emitted during reconciliation."""
    MISSING_SOURCE_HASH = "MISSING_SOURCE_HASH"
    MISSING_SOURCE_NAME = "MISSING_SOURCE_NAME"
    MISSING_IMPORTED_AT = "MISSING_IMPORTED_AT"
    CANNOT_PROVE_SAME_DOCUMENT = "CANNOT_PROVE_SAME_DOCUMENT"


@dataclass(frozen=True)
class EntityDiff:
    """Represents the difference between two entities of the same type."""
    entity_type: str
    entity_id: str
    diff_type: EntityDiffType
    left_value: Any | None = None
    right_value: Any | None = None
    details: str = ""


@dataclass(frozen=True)
class ProvenanceWarning:
    """A warning about missing or insufficient provenance information."""
    warning_type: ProvenanceWarningType
    profile_id: str
    message: str


@dataclass(frozen=True)
class ReconciliationPlan:
    """Complete reconciliation plan between two profiles."""
    left_profile_id: str
    right_profile_id: str
    left_person_id: str | None
    right_person_id: str | None
    identity_comparison: tuple[tuple[str, ...], tuple[str, ...]]
    entity_diffs: tuple[EntityDiff, ...]
    provenance_warnings: tuple[ProvenanceWarning, ...]
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _get_acquisition(record: ProfileRecord | None) -> dict[str, Any]:
    """Extract _acquisition dict from a profile record."""
    if record is None:
        return {}
    data = record.data if isinstance(record.data, dict) else {}
    extensions = data.get("extensions") or {}
    if not isinstance(extensions, dict):
        return {}
    acquisition = extensions.get("_acquisition") or {}
    return acquisition if isinstance(acquisition, dict) else {}


def _extract_provenance_warnings(
    left_record: ProfileRecord | None,
    right_record: ProfileRecord | None,
) -> list[ProvenanceWarning]:
    """Extract provenance warnings from both profiles."""
    warnings: list[ProvenanceWarning] = []
    
    for record, label in [(left_record, "left"), (right_record, "right")]:
        if record is None:
            continue
        profile_id = record.profile_id
        acquisition = _get_acquisition(record)
        
        if not acquisition.get("sourceHash"):
            warnings.append(ProvenanceWarning(
                warning_type=ProvenanceWarningType.MISSING_SOURCE_HASH,
                profile_id=profile_id,
                message=f"Profile '{profile_id}' is missing sourceHash; cannot prove same source document."
            ))
        if not acquisition.get("sourceName"):
            warnings.append(ProvenanceWarning(
                warning_type=ProvenanceWarningType.MISSING_SOURCE_NAME,
                profile_id=profile_id,
                message=f"Profile '{profile_id}' is missing sourceName."
            ))
        if not acquisition.get("importedAt"):
            warnings.append(ProvenanceWarning(
                warning_type=ProvenanceWarningType.MISSING_IMPORTED_AT,
                profile_id=profile_id,
                message=f"Profile '{profile_id}' is missing importedAt."
            ))
    
    left_acq = _get_acquisition(left_record) if left_record else {}
    right_acq = _get_acquisition(right_record) if right_record else {}
    
    if not left_acq.get("sourceHash") or not right_acq.get("sourceHash"):
        warnings.append(ProvenanceWarning(
            warning_type=ProvenanceWarningType.CANNOT_PROVE_SAME_DOCUMENT,
            profile_id="both",
            message="At least one profile lacks sourceHash; cannot determine if they originated from the same source document."
        ))
    
    return warnings


def _normalize_entity_list(entities: Any, key_field: str = "id") -> dict[str, Any]:
    """Normalize a list of entities to a dict keyed by the specified field."""
    if not isinstance(entities, list):
        return {}
    result: dict[str, Any] = {}
    for entity in entities:
        if isinstance(entity, dict) and key_field in entity:
            result[entity[key_field]] = entity
    return result


def _compare_entities(
    left_entities: Any,
    right_entities: Any,
    entity_type: str,
    key_field: str = "id",
) -> list[EntityDiff]:
    """Compare two lists of entities of the same type."""
    left_map = _normalize_entity_list(left_entities, key_field)
    right_map = _normalize_entity_list(right_entities, key_field)
    
    all_ids = set(left_map.keys()) | set(right_map.keys())
    diffs: list[EntityDiff] = []
    
    for entity_id in sorted(all_ids):
        left_entity = left_map.get(entity_id)
        right_entity = right_map.get(entity_id)
        
        if left_entity is not None and right_entity is not None:
            if left_entity == right_entity:
                diffs.append(EntityDiff(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    diff_type=EntityDiffType.SAME,
                    left_value=left_entity,
                    right_value=right_entity,
                ))
            else:
                diffs.append(EntityDiff(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    diff_type=EntityDiffType.CONFLICT,
                    left_value=left_entity,
                    right_value=right_entity,
                    details=f"Entities with same {key_field} have different content",
                ))
        elif left_entity is not None:
            diffs.append(EntityDiff(
                entity_type=entity_type,
                entity_id=entity_id,
                diff_type=EntityDiffType.ONLY_IN_LEFT,
                left_value=left_entity,
            ))
        else:
            diffs.append(EntityDiff(
                entity_type=entity_type,
                entity_id=entity_id,
                diff_type=EntityDiffType.ONLY_IN_RIGHT,
                right_value=right_entity,
            ))
    
    return diffs


def _get_person_id(record: ProfileRecord | None) -> str | None:
    """Extract person.id from a profile record."""
    if record is None:
        return None
    data = record.data if isinstance(record.data, dict) else {}
    person = data.get("person") or {}
    return person.get("id") if isinstance(person, dict) else None


def reconcile_profiles(
    left_record: ProfileRecord | None,
    right_record: ProfileRecord | None,
) -> ReconciliationPlan:
    """Compare two profiles and produce a deterministic reconciliation plan.
    
    Args:
        left_record: First profile record (left side of comparison).
        right_record: Second profile record (right side of comparison).
    
    Returns:
        A deterministic ReconciliationPlan with identity comparison, entity diffs,
        and provenance warnings.
    """
    left_person = (left_record.data.get("person") if left_record and isinstance(left_record.data, dict) else None) or {}
    right_person = (right_record.data.get("person") if right_record and isinstance(right_record.data, dict) else None) or {}
    
    matched, conflicting = _compare_identity(left_person, right_person)
    identity_comparison = (tuple(sorted(matched)), tuple(sorted(conflicting)))
    
    left_person_id = _get_person_id(left_record)
    right_person_id = _get_person_id(right_record)
    
    left_data = left_record.data if left_record and isinstance(left_record.data, dict) else {}
    right_data = right_record.data if right_record and isinstance(right_record.data, dict) else {}
    
    entity_types = [
        ("experiences", "id"),
        ("organizations", "id"),
        ("skills", "id"),
        ("education", "id"),
        ("certifications", "id"),
        ("projects", "id"),
        ("achievements", "id"),
        ("evidence", "id"),
        ("artifacts", "id"),
        ("targetContexts", "id"),
        ("professionalSummaries", "id"),
    ]
    
    all_diffs: list[EntityDiff] = []
    for entity_type, key_field in entity_types:
        left_entities = left_data.get(entity_type, [])
        right_entities = right_data.get(entity_type, [])
        diffs = _compare_entities(left_entities, right_entities, entity_type, key_field)
        all_diffs.extend(diffs)
    
    warnings = _extract_provenance_warnings(left_record, right_record)
    
    return ReconciliationPlan(
        left_profile_id=left_record.profile_id if left_record else "unknown",
        right_profile_id=right_record.profile_id if right_record else "unknown",
        left_person_id=left_person_id,
        right_person_id=right_person_id,
        identity_comparison=identity_comparison,
        entity_diffs=tuple(all_diffs),
        provenance_warnings=tuple(warnings),
    )


def load_profiles_for_reconciliation(
    profiles_root: str | Path,
    left_id: str,
    right_id: str,
) -> tuple[ProfileRecord | None, ProfileRecord | None]:
    """Load two profiles by ID for reconciliation.
    
    Args:
        profiles_root: Root directory of the profiles repository.
        left_id: ID of the first profile (display ID or profile ID).
        right_id: ID of the second profile (display ID or profile ID).
    
    Returns:
        Tuple of (left_record, right_record). Returns None for missing profiles.
    """
    repo = ProfileRepository(profiles_root)
    
    left_record = None
    right_record = None
    
    try:
        left_record = repo.resolve(left_id)
    except Exception:
        pass
    
    try:
        right_record = repo.resolve(right_id)
    except Exception:
        pass
    
    return left_record, right_record


def format_reconciliation_plan(plan: ReconciliationPlan, output_format: str = "yaml") -> str:
    """Format a reconciliation plan for output."""
    import yaml
    
    data = {
        "leftProfileId": plan.left_profile_id,
        "rightProfileId": plan.right_profile_id,
        "leftPersonId": plan.left_person_id,
        "rightPersonId": plan.right_person_id,
        "identityComparison": {
            "matchedOn": list(plan.identity_comparison[0]),
            "conflictingOn": list(plan.identity_comparison[1]),
        },
        "entityDiffs": [
            {
                "entityType": diff.entity_type,
                "entityId": diff.entity_id,
                "diffType": diff.diff_type.value,
                "leftValue": diff.left_value,
                "rightValue": diff.right_value,
                "details": diff.details,
            }
            for diff in plan.entity_diffs
        ],
        "provenanceWarnings": [
            {
                "warningType": w.warning_type.value,
                "profileId": w.profile_id,
                "message": w.message,
            }
            for w in plan.provenance_warnings
        ],
        "generatedAt": plan.generated_at,
    }
    
    if output_format == "json":
        import json
        return json.dumps(data, indent=2, default=str)
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def write_reconciliation_plan(plan: ReconciliationPlan, output_path: str | Path) -> Path:
    """Write a reconciliation plan to a file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = format_reconciliation_plan(plan, output_format="yaml")
    path.write_text(content, encoding="utf-8")
    return path