# CareerOS Verification Framework

## Purpose

This framework provides a generic, reusable way to verify completed work in the repository. It is designed for AI agents and developers who need objective checks for files, directories, and basic file formats without relying on manual text reports.

## Installation

Use Python 3.11+ and install the small dependency set:

```bash
pip install -r requirements.txt
```

## Usage examples

Verify a file exists:

```bash
python verify-task.py --file docs/project/Backlog.md
```

Verify a directory exists:

```bash
python verify-task.py --dir docs/project
```

Validate a JSON file:

```bash
python verify-task.py --json schemas/profile.schema.json
```

Validate a YAML file:

```bash
python verify-task.py --yaml profiles/master-profile.yaml
```

Validate a Markdown file:

```bash
python verify-task.py --markdown docs/project/Backlog.md
```

## Exit codes

- `0` when verification succeeds
- `1` when verification fails
- `2` when the CLI is used incorrectly

## How future verification rules can be added

Add new reusable verification functions to `checks.py` and expose them through the CLI in `verify-task.py`. This keeps the framework extensible for future CI/CD integration and additional repository checks.
