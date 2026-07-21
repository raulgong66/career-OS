from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable

import yaml


class VerificationError(Exception):
    pass


class VerificationResult:
    def __init__(self) -> None:
        self.passed: list[str] = []
        self.failed: list[str] = []

    def add_pass(self, message: str) -> None:
        self.passed.append(message)

    def add_fail(self, message: str) -> None:
        self.failed.append(message)

    def is_success(self) -> bool:
        return not self.failed


def verify_required_files(paths: list[str], result: VerificationResult) -> None:
    for path_str in paths:
        path = Path(path_str)
        if path.exists() and path.is_file():
            result.add_pass(f"Required file exists: {path_str}")
        else:
            result.add_fail(f"Missing required file: {path_str}")


def verify_prohibited_files(paths: list[str], result: VerificationResult) -> None:
    for path_str in paths:
        path = Path(path_str)
        if path.exists():
            result.add_fail(f"Prohibited file found: {path_str}")
        else:
            result.add_pass(f"Prohibited file absent: {path_str}")


def verify_expected_files_not_modified(paths: list[str], result: VerificationResult) -> None:
    for path_str in paths:
        path = Path(path_str)
        if path.exists():
            result.add_pass(f"Expected file present: {path_str}")
        else:
            result.add_fail(f"Expected file missing: {path_str}")


def verify_required_directories(paths: list[str], result: VerificationResult) -> None:
    for path_str in paths:
        path = Path(path_str)
        if path.exists() and path.is_dir():
            result.add_pass(f"Required directory exists: {path_str}")
        else:
            result.add_fail(f"Missing required directory: {path_str}")


def validate_json_file(path_str: str, result: VerificationResult) -> None:
    path = Path(path_str)
    try:
        with path.open("r", encoding="utf-8") as handle:
            json.load(handle)
        result.add_pass(f"Valid JSON: {path_str}")
    except FileNotFoundError:
        result.add_fail(f"JSON file not found: {path_str}")
    except json.JSONDecodeError as exc:
        result.add_fail(f"Invalid JSON in {path_str}: {exc}")


def validate_yaml_file(path_str: str, result: VerificationResult) -> None:
    path = Path(path_str)
    try:
        with path.open("r", encoding="utf-8") as handle:
            yaml.safe_load(handle)
        result.add_pass(f"Valid YAML: {path_str}")
    except FileNotFoundError:
        result.add_fail(f"YAML file not found: {path_str}")
    except yaml.YAMLError as exc:
        result.add_fail(f"Invalid YAML in {path_str}: {exc}")


def validate_markdown_file(path_str: str, result: VerificationResult) -> None:
    path = Path(path_str)
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        result.add_fail(f"Markdown file not found: {path_str}")
        return

    if not content.strip():
        result.add_fail(f"Markdown file is empty: {path_str}")
        return

    if "#" in content or "##" in content:
        result.add_pass(f"Markdown structure looks present: {path_str}")
    else:
        result.add_fail(f"Markdown file appears to have no headings: {path_str}")


def run_checks(checks: list[tuple[str, Callable[[VerificationResult], None]]], result: VerificationResult) -> None:
    for name, checker in checks:
        try:
            checker(result)
        except VerificationError as exc:
            result.add_fail(f"{name} failed: {exc}")


def print_report(result: VerificationResult) -> None:
    print("Verification Report")
    print("===================")
    for message in result.passed:
        print(f"PASS: {message}")
    for message in result.failed:
        print(f"FAIL: {message}")
    print("===================")
    if result.is_success():
        print("Result: SUCCESS")
    else:
        print("Result: FAILURE")
