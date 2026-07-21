# Profile Validator

A simple command-line validator for CareerOS profile files.

## Installation

1. Ensure Python 3.11+ is installed.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Dependencies

- jsonschema
- PyYAML

## Usage

Validate a JSON profile:

```bash
python validate-profile.py profiles/master-profile.json
```

Validate a YAML profile:

```bash
python validate-profile.py profiles/master-profile.yaml
```

The validator will print either:

```text
✔ Profile is valid
```

or:

```text
✘ Profile is invalid
```

and show detailed validation errors with the relevant property path and message.
