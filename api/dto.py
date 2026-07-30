"""DTO mapping layer for the Profile Management API.

Maps canonical profile structures to frontend-oriented DTOs.
The canonical schema remains unchanged.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from careeros.profile_repository import ProfileState


def _get_name(data: dict[str, Any]) -> str:
    """Extract the professional name from a canonical profile."""
    person = data.get("person", {})
    names = person.get("names", [])
    if names:
        return names[0].get("value", "")
    return ""


def _split_name(full_name: str) -> tuple[str, str]:
    """Split a full name into first and last name.
    
    The splitting strategy is an implementation detail of the API layer
    and may evolve without changing the public contract.
    """
    parts = full_name.split(maxsplit=1)
    if len(parts) == 2:
        return parts[0], parts[1]
    if len(parts) == 1:
        return parts[0], ""
    return "", ""


def profile_id_from_name(full_name: str) -> str:
    """Derive a filesystem-safe profile id from a person name."""
    name_id = full_name.strip().lower()
    name_id = "".join(c if c.isalnum() or c in {"-", " "} else "" for c in name_id)
    name_id = "-".join(name_id.split())
    return name_id if name_id else "untitled-profile"


def to_profile_summary(data: dict[str, Any], profile_id: str, state: ProfileState | None = None) -> dict[str, Any]:
    """Map a canonical profile dict to a ProfileSummary DTO."""
    name = _get_name(data)
    person = data.get("person", {})
    positioning = person.get("positioning", {})
    artifacts = data.get("artifacts", [])
    artifact_ids = [a.get("id") for a in artifacts if a.get("id")]
    extensions = data.get("extensions", {})
    imported_at = extensions.get("importedAt", "")

    result: dict[str, Any] = {
        "id": profile_id,
        "name": name,
        "headline": positioning.get("headline", ""),
        "artifactCount": len(artifacts),
        "artifactIds": artifact_ids,
        "importedAt": imported_at,
    }
    if state is not None:
        result["state"] = state.value
    return result


def to_profile_details(data: dict[str, Any], profile_id: str, state: ProfileState | None = None) -> dict[str, Any]:
    """Map a canonical profile dict to a ProfileDetails DTO."""
    name = _get_name(data)
    first_name, last_name = _split_name(name)
    person = data.get("person", {})
    positioning = person.get("positioning", {})
    location = person.get("location", {})
    summaries = data.get("professionalSummaries", [])
    artifacts = data.get("artifacts", [])
    extensions = data.get("extensions", {})
    imported_at = extensions.get("importedAt", "")

    artifact_dtos: list[dict[str, Any]] = []
    for art in artifacts:
        artifact_dtos.append({
            "id": art.get("id", ""),
            "type": art.get("artifactType", ""),
            "name": art.get("title", ""),
            "sourceCount": len(art.get("sourceRefs", [])),
        })

    result: dict[str, Any] = {
        "id": profile_id,
        "person": {
            "firstName": first_name,
            "lastName": last_name,
            "headline": positioning.get("headline", ""),
            "city": location.get("city"),
            "country": location.get("country"),
            "languages": person.get("languages", []),
        },
        "artifacts": artifact_dtos,
        "summary": summaries[0].get("text") if summaries else None,
        "importedAt": imported_at,
    }
    if state is not None:
        result["state"] = state.value
    return result


def to_import_response(data: dict[str, Any], profile_id: str, state: ProfileState | None = None) -> dict[str, Any]:
    """Map a canonical profile dict to an ImportResponse DTO."""
    profile = to_profile_summary(data, profile_id, state=state)
    return {
        "profileId": profile_id,
        "profile": profile,
    }
