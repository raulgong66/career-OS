# Canonical Profile Model

Version: 1.0

## Purpose and Scope

The Canonical Profile Model defines the conceptual source of truth for a professional profile in CareerOS. It describes the stable professional data from which CVs, resumes, LinkedIn profiles, portfolios, cover letters, interview preparation, and other career artifacts are derived.

This model is implementation-independent. It does not define file formats, schemas, storage mechanisms, automation workflows, or generated document templates. Its purpose is to establish shared language, boundaries, and relationships for future implementation decisions.

## Design Principles

1. The canonical profile is the source of truth; generated artifacts are derived views.
2. Facts, assumptions, and recommendations must remain distinguishable.
3. Profile data should be reusable across multiple audiences, roles, regions, and artifact types.
4. The model should support evidence-based professional claims.
5. The model should separate durable career facts from temporary positioning choices.
6. Extensions should add clarity without forcing architecture redesign.

## Core Entities

### Person

The professional individual represented by the profile. This includes identity, contact preferences, location context, language preferences, and high-level professional positioning.

### Professional Summary

A concise expression of the person's current professional identity, value proposition, target direction, and positioning themes. Summaries may vary by audience, but they should be derived from canonical facts and selected emphasis.

### Experience

A role, engagement, project assignment, business activity, or other professional period. Experience captures organization context, role scope, responsibilities, outcomes, dates, location, and relevant employment or engagement type.

### Organization

An employer, client, institution, project sponsor, or other entity connected to experience, education, certification, or portfolio work.

### Project

A distinct body of work that demonstrates capability. Projects may be professional, academic, portfolio-based, or self-directed. They may connect to experiences, skills, outcomes, artifacts, and evidence.

### Skill

A capability, method, tool, technology, domain competency, language, or working style that can be demonstrated through experience, projects, education, certifications, or evidence.

### Achievement

A measurable or meaningful result attributable to the person. Achievements should be connected to supporting context such as an experience, project, skill, or organization.

### Evidence

Supporting material that substantiates a claim. Evidence may include links, documents, portfolio artifacts, certificates, metrics, testimonials, publications, or other references.

### Education

Formal or structured learning history, including degrees, programs, courses, institutions, fields of study, dates, and relevant outcomes.

### Certification

A credential, license, certificate, or verified training result issued by an organization or authority.

### Artifact

A generated or curated output intended for use in a career context, such as a CV, resume, LinkedIn profile, portfolio page, cover letter, interview brief, biography, or presentation.

### Target Context

The audience, role, market, industry, geography, seniority level, language, or opportunity context that determines how canonical data is selected, emphasized, and transformed into an artifact.

## Relationships Between Entities

The Person is the central entity. Experiences, projects, education, certifications, skills, achievements, and evidence describe or support the Person's professional profile.

Experiences may involve one or more organizations and may demonstrate multiple skills. Experiences may also contain achievements and connect to projects.

Projects may be linked to experiences or exist independently as portfolio work. Projects may demonstrate skills, produce artifacts, and be supported by evidence.

Skills are demonstrated through experiences, projects, education, certifications, achievements, and evidence. A skill should be most useful when connected to proof rather than listed in isolation.

Achievements belong to a context such as an experience, project, education record, or certification. They may be supported by evidence and may demonstrate one or more skills.

Evidence supports claims made across the profile. Evidence may substantiate achievements, projects, certifications, education, or experience details.

Artifacts are derived from canonical profile entities and shaped by a target context. They should not become the source of truth for profile facts.

Target contexts guide selection, ordering, tone, language, level of detail, and emphasis when generating artifacts.

## Canonical Data and Generated Outputs

Canonical data represents durable professional facts and structured claims about the person. It should be maintained independently from any single CV, resume, LinkedIn profile, portfolio page, or cover letter.

Generated outputs are views of the canonical profile. They may omit details, reorder content, rephrase summaries, translate language, or emphasize different skills and achievements for a target context.

Generated outputs may include editorial choices, but they should not introduce unsupported claims. When an output reveals missing or outdated canonical data, the canonical profile should be updated first, then the output regenerated or revised.

## Versioning Considerations

The canonical profile should support change over time without losing important history. Changes may include new roles, revised achievements, updated skills, new certifications, corrected facts, or retired positioning.

Major conceptual changes to the model should be recorded in the project's Architecture Decision Records or other designated decision log. Generated artifacts should identify which profile version, date, or source state they were derived from when that traceability is useful.

Versioning should distinguish between factual profile changes and presentation changes. A corrected employment date is a profile data change; rewriting a resume summary for a specific role is an artifact change.

## Extensibility Guidelines

New entities should be added only when existing entities cannot clearly represent the concept. Extensions should preserve the distinction between canonical data, target context, and generated output.

Additional fields, categories, or relationships should support evidence-based reuse across artifacts. They should avoid encoding one template, platform, or storage format into the conceptual model.

The model should remain stable enough to guide implementation while allowing future support for localization, privacy boundaries, access levels, richer evidence, artifact generation workflows, and role-specific profile variants.
