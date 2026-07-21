# Canonical Profile Workspace

## Purpose

This directory holds the canonical master profile for CareerOS. The master profile is the single source of truth for professional facts that may later be used to generate CVs, resumes, LinkedIn content, portfolios, cover letters, and other career artifacts.

## Why this is the single source of truth

Generated artifacts must derive from the canonical profile rather than from separate, inconsistent copies. Keeping one structured profile ensures that updates, evidence, and positioning choices remain traceable and reusable.

## Sources that may inform the profile

The master profile may be built from any trustworthy source that documents professional reality, including:

- CVs and resumes
- LinkedIn profiles
- Certificates and credentials
- Project documentation
- Performance reviews
- Portfolio materials
- Other evidence-based professional records

## Rule for generated artifacts

All generated artifacts must be derived from this profile. If a value is not represented in the master profile, it should not appear in a generated artifact unless it is explicitly added and approved as canonical data.

## Validation

Use the Profile Validator to check the structure of the profile:

```bash
python tools/validator/validate-profile.py profiles/master-profile.yaml
```
