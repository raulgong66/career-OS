# Placeholder Conventions

## Purpose

This document defines the repository-wide placeholder convention for CareerOS templates and data files. It ensures that missing information is represented consistently, clearly, and without inventing facts.

## Scope

These conventions apply to templates, example files, and other repository documents that intentionally contain incomplete content. They do not change the JSON Schema or alter the meaning of validated data structures.

## Placeholder Definitions

- `<REQUIRED>`: A mandatory value that has not yet been provided.
- `<OPTIONAL>`: An optional value that is intentionally left blank.
- `<AUTO>`: A value that will be generated automatically by CareerOS.
- `<TBD>`: A design or business decision that is still pending.
- `<UNKNOWN>`: A value that is currently unknown but is expected to become known later.

## Usage Rules

- Never use `TODO` as a data value.
- `TODO` is allowed only inside comments.
- Comments should explain what belongs in a field.
- Placeholder values represent missing data, not invented facts.
- Generated artifacts must never contain placeholders.
- JSON Schema remains independent of placeholder conventions.
- Placeholder validation belongs to the verification framework, not the JSON Schema.

## Examples

```yaml
profileVersion: <REQUIRED>
person:
  id: <REQUIRED>
  names:
    - value: <REQUIRED>
      usage: <OPTIONAL>
```

```yaml
# TODO: Replace this placeholder with the final approved value.
positioning:
  headline: <REQUIRED>
```

## Future Validation Considerations

Future verification rules may check that placeholder values are used consistently and that generated artifacts do not retain unresolved placeholders. These checks should be implemented in the verification framework rather than in the JSON Schema.
