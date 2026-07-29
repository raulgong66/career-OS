from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from careeros.exceptions import CareerOSException


class YamlWriteError(CareerOSException):
    pass


class YamlWriter:
    # Staging directory: generated profiles are written here first,
    # before Human Review approval. Only reviewed and approved profiles
    # should be moved to the canonical profiles/ directory.
    # This prevents unverified data from entering the delivery pipeline.
    DEFAULT_OUTPUT_DIR = Path("profiles/staging")

    def write(
        self,
        profile: dict[str, Any],
        output_path: str | Path | None = None,
    ) -> Path:
        path = self._resolve_path(profile, output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_text(
                yaml.safe_dump(profile, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
        except OSError as exc:
            raise YamlWriteError(f"Failed to write profile to {path}: {exc}") from exc
        return path

    def _resolve_path(
        self,
        profile: dict[str, Any],
        output_path: str | Path | None,
    ) -> Path:
        if output_path is not None:
            return Path(output_path).expanduser().resolve()
        person_id = profile.get("person", {}).get("id", "unknown")
        return Path.cwd() / self.DEFAULT_OUTPUT_DIR / f"{person_id}-profile.yaml"
