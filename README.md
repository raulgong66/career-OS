# CareerOS

CareerOS is a schema-driven toolkit for managing professional profile, application, and project data.

## Installation

```bash
python3 -m pip install -e .
```

## Usage

### CLI

```bash
careeros --help
careeros version
careeros doctor
careeros schemas list
careeros schemas info profile
careeros validate profile profiles/master-profile.yaml
careeros create company company.json
careeros show company company.json
careeros list company .
careeros search company name Example
```

### API

```bash
python3 -m uvicorn api.main:app --reload
```

Then open the docs at:

```text
http://127.0.0.1:8000/docs
```
