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
    """Split a full name into first and last name."""
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


def _build_org_lookup(data: dict[str, Any]) -> dict[str, str]:
    """Build a lookup from organization id to name."""
    orgs = data.get("organizations", [])
    return {org.get("id"): org.get("name", "") for org in orgs}


def _map_date_range(dr: Any) -> dict[str, Any] | None:
    """Map a dateRange dict to a flat DTO."""
    if not dr or not isinstance(dr, dict):
        return None
    result: dict[str, Any] = {}
    if dr.get("start"):
        result["start"] = dr["start"]
    if dr.get("end"):
        result["end"] = dr["end"]
    if dr.get("isCurrent"):
        result["isCurrent"] = True
    if dr.get("label"):
        result["label"] = dr["label"]
    return result if result else None


def _map_experiences(data: dict[str, Any], org_lookup: dict[str, str]) -> list[dict[str, Any]]:
    """Map canonical experiences to DTOs, resolving organization references."""
    experiences = data.get("experiences", [])
    result: list[dict[str, Any]] = []
    for exp in experiences:
        org_refs = exp.get("organizationRefs", [])
        org_name = ""
        for ref in org_refs:
            if ref.get("id") in org_lookup:
                org_name = org_lookup[ref["id"]]
                break
        result.append({
            "id": exp.get("id", ""),
            "title": exp.get("title", ""),
            "organization": org_name,
            "dateRange": _map_date_range(exp.get("dateRange")),
            "scope": exp.get("scope", ""),
            "engagementType": exp.get("engagementType", ""),
        })
    return result


def _map_skills(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Map canonical skills to DTOs."""
    skills = data.get("skills", [])
    result: list[dict[str, Any]] = []
    for skill in skills:
        entry: dict[str, Any] = {
            "id": skill.get("id", ""),
            "name": skill.get("name", ""),
            "category": skill.get("category", ""),
            "description": skill.get("description", ""),
        }
        ext = skill.get("extensions", {})
        if ext.get("proficiency"):
            entry["proficiency"] = ext["proficiency"]
        result.append(entry)
    return result


def _map_education(data: dict[str, Any], org_lookup: dict[str, str]) -> list[dict[str, Any]]:
    """Map canonical education to DTOs, resolving institution references."""
    education = data.get("education", [])
    result: list[dict[str, Any]] = []
    for edu in education:
        inst_ref = edu.get("institutionRef")
        inst_name = ""
        if inst_ref and inst_ref.get("id") in org_lookup:
            inst_name = org_lookup[inst_ref["id"]]
        result.append({
            "id": edu.get("id", ""),
            "institution": inst_name,
            "program": edu.get("program", ""),
            "fieldOfStudy": edu.get("fieldOfStudy", ""),
            "dateRange": _map_date_range(edu.get("dateRange")),
        })
    return result


def _map_certifications(data: dict[str, Any], org_lookup: dict[str, str]) -> list[dict[str, Any]]:
    """Map canonical certifications to DTOs, resolving issuer references."""
    certifications = data.get("certifications", [])
    result: list[dict[str, Any]] = []
    for cert in certifications:
        issuer_ref = cert.get("issuerRef")
        issuer_name = ""
        if issuer_ref and issuer_ref.get("id") in org_lookup:
            issuer_name = org_lookup[issuer_ref["id"]]
        result.append({
            "id": cert.get("id", ""),
            "name": cert.get("name", ""),
            "issuer": issuer_name,
            "dateRange": _map_date_range(cert.get("dateRange")),
        })
    return result


def _map_projects(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Map canonical projects to DTOs."""
    projects = data.get("projects", [])
    result: list[dict[str, Any]] = []
    for proj in projects:
        result.append({
            "id": proj.get("id", ""),
            "name": proj.get("name", ""),
            "description": proj.get("description", ""),
        })
    return result


def _map_professional_summaries(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Map canonical professional summaries to DTOs."""
    summaries = data.get("professionalSummaries", [])
    result: list[dict[str, Any]] = []
    for s in summaries:
        result.append({
            "id": s.get("id", ""),
            "label": s.get("label", ""),
            "text": s.get("text", ""),
        })
    return result


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

    org_lookup = _build_org_lookup(data)

    def _infer_artifact_type(art: dict[str, Any]) -> str:
        explicit = art.get("artifactType")
        if explicit:
            return str(explicit)
        art_id = str(art.get("id", "")).lower()
        title = str(art.get("title", "")).lower()
        if "interest" in art_id or "interest" in title:
            return "INTEREST_LETTER"
        if "cover" in art_id or "cover" in title:
            return "COVER_LETTER"
        if "cv" in art_id or "cv" in title or "resume" in art_id or "resume" in title:
            return "CV"
        return ""

    artifact_dtos: list[dict[str, Any]] = []
    for art in artifacts:
        artifact_dtos.append({
            "id": art.get("id", ""),
            "type": _infer_artifact_type(art),
            "name": art.get("title", ""),
            "sourceCount": len(art.get("sourceRefs", [])),
            "status": art.get("status", "current"),
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
        "professionalSummaries": _map_professional_summaries(data),
        "experiences": _map_experiences(data, org_lookup),
        "skills": _map_skills(data),
        "education": _map_education(data, org_lookup),
        "certifications": _map_certifications(data, org_lookup),
        "projects": _map_projects(data),
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
