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

    def delete(self, profile_id: str) -> None:
        record = self.get(profile_id)
        record.path.unlink()

    def get_state_dir(self, state: ProfileState) -> Path:
        return self._state_dir(state)
