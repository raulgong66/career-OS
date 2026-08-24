"""Deterministic import classification for CareerOS Phase 2A.

Classifies a freshly imported staging profile against the existing profile
store (staging + canonical) using only deterministic signals:

* source document hash (``extensions._acquisition.sourceHash``)
* identity fields already present in the canonical schema (``person.names``,
  ``person.contact.email``, ``person.contact.phone``, ``person.links``)

Phase 2A never merges or promotes profiles: it detects and preserves, and
leaves human/explicit reconciliation for a later phase.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from .acquisition.utils import person_id_from_name

NEW_PERSON = "NEW_PERSON"
SAME_DOCUMENT = "SAME_DOCUMENT"
POSSIBLE_SAME_PERSON = "POSSIBLE_SAME_PERSON"
IDENTITY_CONFLICT = "IDENTITY_CONFLICT"


@dataclass(frozen=True)
class CandidateMatch:
    """An existing profile that matched a new import on deterministic signals."""

    profile_id: str
    matched_on: tuple[str, ...] = ()
    conflicting_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class ImportClassification:
    """Result of classifying a new import against the existing profile store."""

    result: str
    candidates: tuple[CandidateMatch, ...] = ()


def source_hash_for_bytes(contents: bytes) -> str:
    """Return the stable SHA-256 digest of raw uploaded document bytes."""
    return hashlib.sha256(contents).hexdigest()


_SAFE_EXTENSION = re.compile(r"^\.[a-z0-9]{1,16}$")


def retain_source(contents: bytes, sources_dir: str | Path, source_hash: str, suffix: str) -> Path:
    """Persist raw uploaded bytes under ``<source_hash><suffix>``.

    The retained filename is derived solely from the content hash and the
    file's final extension, never from raw user input, so it cannot be used
    for path traversal or filename injection.
    """
    sources_dir = Path(sources_dir)
    sources_dir.mkdir(parents=True, exist_ok=True)
    candidate = (suffix or "").lower()
    safe_suffix = candidate if _SAFE_EXTENSION.match(candidate) else ""
    path = sources_dir / f"{source_hash}{safe_suffix}"
    path.write_bytes(contents)
    return path


def _fold_phone(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _href(links: Sequence[Any], label: str) -> str:
    for link in links or []:
        if isinstance(link, dict) and link.get("label") == label and link.get("href"):
            return str(link["href"]).strip().lower()
    return ""


def _person_signals(person: dict[str, Any] | None) -> dict[str, Any]:
    """Extract the deterministic identity signals available on a canonical person."""
    person = person or {}
    contact = person.get("contact") or {}
    names = [
        str(n.get("value", "")).strip()
        for n in (person.get("names") or [])
        if isinstance(n, dict) and n.get("value")
    ]
    links = person.get("links") or []
    return {
        "names": names,
        "email": str(contact.get("email") or "").strip().lower(),
        "phone": _fold_phone(contact.get("phone")),
        "linkedin": _href(links, "LinkedIn"),
        "github": _href(links, "GitHub"),
    }


def _name_slug(name: str) -> str:
    return person_id_from_name(name)


def _token_set(slugs: Sequence[str]) -> set[str]:
    tokens: set[str] = set()
    for slug in slugs:
        tokens |= set(slug.split("-")) - {"person"}
    return tokens


def _compare_identity(
    new_person: dict[str, Any] | None,
    existing_person: dict[str, Any] | None,
) -> tuple[list[str], list[str]]:
    """Deterministically compare two canonical persons.

    Returns ``(matched, conflicting)`` lists of signal names. A match is
    strong (exact email/phone/linkedin/github/name) or a conservative
    name-token containment candidate. A conflict is a strong name signal that
    disagrees with a present-but-different email or phone.
    """
    new_sig = _person_signals(new_person)
    old_sig = _person_signals(existing_person)

    matched: list[str] = []
    for signal in ("email", "phone", "linkedin", "github"):
        if new_sig[signal] and new_sig[signal] == old_sig[signal]:
            matched.append(signal)

    new_slugs = sorted({_name_slug(n) for n in new_sig["names"] if n})
    old_slugs = sorted({_name_slug(n) for n in old_sig["names"] if n})

    exact_name = bool(new_slugs and old_slugs and set(new_slugs) & set(old_slugs))
    if exact_name:
        matched.append("name")

    token_match = False
    if new_slugs and old_slugs and not exact_name:
        new_tokens = _token_set(new_slugs)
        old_tokens = _token_set(old_slugs)
        if (
            min(len(new_tokens), len(old_tokens)) >= 2
            and (new_tokens <= old_tokens or old_tokens <= new_tokens)
        ):
            token_match = True
            matched.append("name-tokens")

    conflict: list[str] = []
    if exact_name or token_match:
        if new_sig["email"] and old_sig["email"] and new_sig["email"] != old_sig["email"]:
            conflict.append("email")
        if new_sig["phone"] and old_sig["phone"] and new_sig["phone"] != old_sig["phone"]:
            conflict.append("phone")

    return matched, conflict


def classify_import(
    existing_profiles: Sequence[Any],
    source_hash: str,
    profile_data: dict[str, Any],
    *,
    exclude_profile_id: str | None = None,
) -> ImportClassification:
    """Classify a freshly imported profile against existing profile records.

    Args:
        existing_profiles: Iterable of profile records exposing ``profile_id``
            and ``data`` (e.g. ``ProfileRepository.list()``).
        source_hash: SHA-256 of the raw uploaded document bytes.
        profile_data: The freshly imported canonical profile payload.
        exclude_profile_id: Profile id to skip (the just-imported profile).

    Returns:
        ``SAME_DOCUMENT`` when the exact source bytes were already imported,
        otherwise ``IDENTITY_CONFLICT``, ``POSSIBLE_SAME_PERSON``, or
        ``NEW_PERSON``. Never merges and never promotes.
    """
    new_hash = (source_hash or "").strip().lower()
    new_person = (profile_data or {}).get("person") or {}

    if new_hash:
        for record in existing_profiles:
            if exclude_profile_id and record.profile_id == exclude_profile_id:
                continue
            data = getattr(record, "data", None) or {}
            acq = (data.get("extensions") or {}).get("_acquisition") or {}
            if acq.get("sourceHash") == new_hash:
                return ImportClassification(
                    result=SAME_DOCUMENT,
                    candidates=(
                        CandidateMatch(
                            profile_id=record.profile_id,
                            matched_on=("sourceHash",),
                        ),
                    ),
                )

    candidates: list[CandidateMatch] = []
    conflicts: list[CandidateMatch] = []
    for record in existing_profiles:
        if exclude_profile_id and record.profile_id == exclude_profile_id:
            continue
        data = getattr(record, "data", None) or {}
        matched, conflicting = _compare_identity(new_person, data.get("person") or {})
        if conflicting:
            conflicts.append(
                CandidateMatch(
                    profile_id=record.profile_id,
                    matched_on=tuple(matched),
                    conflicting_on=tuple(conflicting),
                )
            )
        elif matched:
            candidates.append(
                CandidateMatch(
                    profile_id=record.profile_id,
                    matched_on=tuple(matched),
                )
            )

    if conflicts:
        return ImportClassification(result=IDENTITY_CONFLICT, candidates=tuple(conflicts + candidates))
    if candidates:
        return ImportClassification(result=POSSIBLE_SAME_PERSON, candidates=tuple(candidates))
    return ImportClassification(result=NEW_PERSON, candidates=())
