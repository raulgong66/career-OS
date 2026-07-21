#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable

from checks import (
    VerificationError,
    VerificationResult,
    print_report,
    run_checks,
    validate_json_file,
    validate_markdown_file,
    validate_yaml_file,
    verify_expected_files_not_modified,
    verify_prohibited_files,
    verify_required_directories,
    verify_required_files,
)


class CLIError(Exception):
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generic verification framework for CareerOS tasks")
    parser.add_argument("--file", action="append", default=[], help="Verify that a file exists")
    parser.add_argument("--dir", action="append", default=[], help="Verify that a directory exists")
    parser.add_argument("--json", action="append", default=[], help="Validate a JSON file")
    parser.add_argument("--yaml", action="append", default=[], help="Validate a YAML file")
    parser.add_argument("--markdown", action="append", default=[], help="Validate a Markdown file")
    parser.add_argument("--required-file", action="append", default=[], help="Verify that a required file exists")
    parser.add_argument("--prohibited-file", action="append", default=[], help="Verify that a prohibited file does not exist")
    parser.add_argument("--expected-file", action="append", default=[], help="Verify that an expected file is present")
    parser.add_argument("--required-dir", action="append", default=[], help="Verify that a required directory exists")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    result = VerificationResult()
    checks: list[tuple[str, Callable[[VerificationResult], None]]] = []

    if args.file:
        checks.append(("file existence", lambda res: verify_required_files(args.file, res)))
    if args.dir:
        checks.append(("directory existence", lambda res: verify_required_directories(args.dir, res)))
    if args.json:
        checks.append(("json validation", lambda res: [validate_json_file(path, res) for path in args.json]))
    if args.yaml:
        checks.append(("yaml validation", lambda res: [validate_yaml_file(path, res) for path in args.yaml]))
    if args.markdown:
        checks.append(("markdown validation", lambda res: [validate_markdown_file(path, res) for path in args.markdown]))
    if args.required_file:
        checks.append(("required files", lambda res: verify_required_files(args.required_file, res)))
    if args.prohibited_file:
        checks.append(("prohibited files", lambda res: verify_prohibited_files(args.prohibited_file, res)))
    if args.expected_file:
        checks.append(("expected files", lambda res: verify_expected_files_not_modified(args.expected_file, res)))
    if args.required_dir:
        checks.append(("required directories", lambda res: verify_required_directories(args.required_dir, res)))

    if not checks:
        parser.error("No verification options provided")

    run_checks(checks, result)
    print_report(result)
    return 0 if result.is_success() else 1


if __name__ == "__main__":
    sys.exit(main())
