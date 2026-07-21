#!/usr/bin/env python3
"""Validate a CareerOS profile against the canonical JSON Schema."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, ValidationError


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_schema(schema_path: Path) -> dict[str, Any]:
    with schema_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_profile(profile_path: Path) -> Any:
    suffix = profile_path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        with profile_path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle)
    if suffix == ".json":
        with profile_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    with profile_path.open("r", encoding="utf-8") as handle:
        text = handle.read()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return yaml.safe_load(text)


def format_path(path: list[str | int]) -> str:
    if not path:
        return "$"
    rendered = "$"
    for part in path:
        if isinstance(part, int):
            rendered += f"[{part}]"
        else:
            rendered += f".{part}" if rendered != "$" else f".{part}"
    return rendered


def validate_profile(profile: Any, schema: dict[str, Any]) -> list[ValidationError]:
    validator = Draft202012Validator(schema)
    return list(validator.iter_errors(profile))


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python validate-profile.py <profile-file>")
        return 2

    profile_path = Path(sys.argv[1]).expanduser().resolve()
    if not profile_path.exists():
        print(f"✘ Profile file not found: {profile_path}")
        return 1

    schema_path = repo_root() / "schemas" / "profile.schema.json"
    if not schema_path.exists():
        print(f"✘ Schema file not found: {schema_path}")
        return 1

    try:
        schema = load_schema(schema_path)
        profile = load_profile(profile_path)
    except (json.JSONDecodeError, yaml.YAMLError, OSError) as exc:
        print(f"✘ Failed to load profile or schema: {exc}")
        return 1

    errors = validate_profile(profile, schema)
    if not errors:
        print("✔ Profile is valid")
        return 0

    print("✘ Profile is invalid")
    for error in errors:
        property_path = format_path(list(error.absolute_path))
        print(f"- {property_path}: {error.message}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
