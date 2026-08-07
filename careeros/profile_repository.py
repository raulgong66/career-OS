from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, NamedTuple

import yaml

from careeros.exceptions import EntityNotFoundError


class ProfileState(str, Enum):
    STAGING = "staging"
    CANONICAL = "canonical"
    ARCHIVED = "archived"


STATE_DIR_MAP: dict[ProfileState, str] = {
    ProfileState.STAGING: "staging",
    ProfileState.CANONICAL: ".",
    ProfileState.ARCHIVED: "archived",
}

SEARCH_PRECEDENCE: list[ProfileState] = [
    ProfileState.STAGING,
    ProfileState.CANONICAL,
    ProfileState.ARCHIVED,
]


class ProfileRecord(NamedTuple):
    profile_id: str
    state: ProfileState
    path: Path
    data: dict[str, Any]


class ProfileRepository:
    def __init__(self, profiles_root: str | Path) -> None:
        self._root = Path(profiles_root).expanduser().resolve()

    def _state_dir(self, state: ProfileState) -> Path:
        rel = STATE_DIR_MAP[state]
        return self._root / rel if rel != "." else self._root

    def _find(self, profile_id: str) -> ProfileRecord | None:
        for state in SEARCH_PRECEDENCE:
            state_dir = self._state_dir(state)
            for ext in (".yaml", ".yml", ".json"):
                candidate = state_dir / f"{profile_id}{ext}"
                if candidate.is_file():
                    try:
                        with candidate.open("r", encoding="utf-8") as fh:
                            data: dict[str, Any] = (
                                __import__("json").load(fh) if ext == ".json" else yaml.safe_load(fh)
                            )
                    except Exception:
                        continue
                    return ProfileRecord(
                        profile_id=profile_id, state=state, path=candidate, data=data
                    )
        return None

    def get(self, profile_id: str) -> ProfileRecord:
        record = self._find(profile_id)
        if record is None:
            raise EntityNotFoundError(f"Profile not found: {profile_id}")
        return record

    def resolve(self, display_id: str) -> ProfileRecord:
        """Resolve a user-facing profile id to a ProfileRecord.

        Tries the display id as-is, then with a ``-profile`` suffix
        (matching repository file stems), then scans all profiles for
        a matching ``person.id``.
        """
        for candidate in (display_id, f"{display_id}-profile"):
            record = self._find(candidate)
            if record is not None:
                return record
        for record in self.list():
            person = (record.data or {}).get("person") or {}
            if person.get("id") == display_id:
                return record
        raise EntityNotFoundError(f"Profile not found: {display_id}")

    def list(self) -> list[ProfileRecord]:
        results: list[ProfileRecord] = []
        seen: set[str] = set()
        for state in SEARCH_PRECEDENCE:
            state_dir = self._state_dir(state)
            if not state_dir.is_dir():
                continue
            for path in sorted(state_dir.iterdir()):
                if path.suffix not in {".yaml", ".yml", ".json"} or not path.is_file():
                    continue
                profile_id = path.stem
                if profile_id in seen:
                    continue
                seen.add(profile_id)
                try:
                    with path.open("r", encoding="utf-8") as fh:
                        data = (
                            __import__("json").load(fh)
                            if path.suffix == ".json"
                            else yaml.safe_load(fh)
                        )
                except Exception:
                    continue
                results.append(
                    ProfileRecord(profile_id=profile_id, state=state, path=path, data=data)
                )
        return results

    def exists(self, profile_id: str) -> bool:
        return self._find(profile_id) is not None

    def _find_in_state(self, profile_id: str, state: ProfileState) -> ProfileRecord | None:
        """Search for a profile file in exactly one state directory."""
        state_dir = self._state_dir(state)
        if not state_dir.is_dir():
            return None
        for ext in (".yaml", ".yml", ".json"):
            candidate = state_dir / f"{profile_id}{ext}"
            if candidate.is_file():
                try:
                    with candidate.open("r", encoding="utf-8") as fh:
                        data: dict[str, Any] = (
                            __import__("json").load(fh) if ext == ".json" else yaml.safe_load(fh)
                        )
                except Exception:
                    continue
                return ProfileRecord(
                    profile_id=profile_id, state=state, path=candidate, data=data
                )
        return None

    def archive(self, profile_id: str) -> ProfileRecord:
        """Move a profile from staging or canonical to the archived directory."""
        record = self.get(profile_id)
        if record.state == ProfileState.ARCHIVED:
            raise ValueError(f"Profile '{profile_id}' is already archived.")
        archived_dir = self._state_dir(ProfileState.ARCHIVED)
        archived_dir.mkdir(parents=True, exist_ok=True)
        dest = archived_dir / record.path.name
        record.path.rename(dest)
        return ProfileRecord(
            profile_id=profile_id, state=ProfileState.ARCHIVED, path=dest, data=record.data
        )

    def restore(self, profile_id: str) -> ProfileRecord:
        """Move a profile from archived back to the staging directory."""
        record = self._find_in_state(profile_id, ProfileState.ARCHIVED)
        if record is None:
            raise EntityNotFoundError(f"Profile not found in archived: {profile_id}.")
        staging_dir = self._state_dir(ProfileState.STAGING)
        staging_dir.mkdir(parents=True, exist_ok=True)
        dest = staging_dir / record.path.name
        record.path.rename(dest)
        return ProfileRecord(
            profile_id=profile_id, state=ProfileState.STAGING, path=dest, data=record.data
        )

    def delete(self, profile_id: str) -> None:
        record = self.get(profile_id)
        record.path.unlink()

    def get_state_dir(self, state: ProfileState) -> Path:
        return self._state_dir(state)


def profile_display_name(data: dict[str, Any] | None) -> str:
    """Best-effort human-readable display name for a profile payload.

    Prefers the ``professional`` name, then any named entry, then legacy
    first/last/full name fields, falling back to the profile id.
    """
    person = (data or {}).get("person") or {}
    for name in person.get("names", []):
        if name.get("usage") == "professional" and name.get("value"):
            return str(name["value"])
    for name in person.get("names", []):
        if name.get("value"):
            return str(name["value"])
    first = person.get("firstName") or ""
    last = person.get("lastName") or ""
    full = person.get("fullName") or ""
    return full or f"{first} {last}".strip() or str(person.get("id", "Unnamed Profile"))


def profile_display_id(profile_id: str) -> str:
    """User-facing profile id: the repository file stem without a ``-profile`` suffix.

    ``person-hechavarria-profile.yaml`` is addressed as ``person-hechavarria``.
    """
    suffix = "-profile"
    return profile_id[: -len(suffix)] if profile_id.endswith(suffix) else profile_id
