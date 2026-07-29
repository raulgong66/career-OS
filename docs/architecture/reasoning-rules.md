# Reasoning Rules

This document catalogs the deterministic rules that the Reasoning Engine will
implement. Each rule is a pure function over the Knowledge Graph. Rules are
organised by Rule Group.

No implementation details are included. Only the conceptual design, inputs,
outputs, and behaviour.

---

## Rule Group: Experience

### strongest_experience

Identifies the single most senior or impactful experience based on title,
scope, and organizational prominence.

**Input:** Experience nodes and their AT_ORGANIZATION edges.
**Output:** A single Finding pointing to the highest-ranked experience node.
**Behaviour:** Ranks experiences by title hierarchy (CXO > VP > Director >
Manager > IC), then by scope length, then by organization profile. Returns
the top-ranked experience with its supporting graph references.

### recent_experience

Identifies the chronologically most recent experience.

**Input:** Experience nodes with dateRange properties.
**Output:** A Finding pointing to the experience with the latest end date.
**Behaviour:** Computes recency from the `endDate` property. Experiences
with `isCurrent: true` are considered most recent. Where no end date exists,
uses start date. Ties are resolved by duration (longer is preferred).

### career_progression

Analyses the trajectory of roles over time.

**Input:** All experience nodes, ordered by dateRange.
**Output:** A Finding describing the progression pattern (upward, lateral,
varied, specialised) with supporting experience references.
**Behaviour:** Compares consecutive experience titles and scopes. Upward
progression is detected when each subsequent role has higher or broader
responsibility. Lateral moves are detected when title level is consistent
but domain changes. Returns the detected pattern and the experiences that
define it.

### leadership_evidence

Determines whether the profile contains leadership experience.

**Input:** Experience nodes with scope and engagementType properties.
**Output:** A Finding with a boolean value and supporting experience references.
**Behaviour:** Scans experience titles for leadership keywords (lead, head,
chief, director, manager, owner, principal) and scope descriptions for team
references. An experience is classified as leadership if title or scope
indicates responsibility for people, teams, or organisational outcomes.

### management_evidence

Determines whether the profile contains people management experience.

**Input:** Experience nodes with scope properties.
**Output:** A Finding referencing experiences with explicit management
responsibility.
**Behaviour:** A stricter subset of leadership_evidence. Requires explicit
mention of direct reports, team size, hiring, performance management, or
reporting structure in the experience scope or technologies.

---

## Rule Group: Skills

### most_used_technology

Identifies the technology or skill used across the highest number of
experiences.

**Input:** USES_SKILL edges from Experience nodes to Skill nodes.
**Output:** A Finding pointing to the Skill node with the most incoming
USES_SKILL edges.
**Behaviour:** Counts USES_SKILL edges per Skill node. Returns the skill
with the highest count. Ties are resolved by proficiency level, then
alphabetically.

### skill_recency

Determines when each skill was last actively used.

**Input:** Skill nodes, USES_SKILL edges, Experience dateRange properties.
**Output:** A Finding per skill containing the date of last use.
**Behaviour:** For each Skill node, traverses its USED_IN_EXPERIENCE edges
to find the most recent Experience end date. Skills with no evidence edges
are marked as "last used unknown."

### years_of_experience_per_skill

Computes total years of experience per skill.

**Input:** Skill nodes, USES_SKILL edges, Experience dateRange properties.
**Output:** Findings mapping each skill to its total duration in years.
**Behaviour:** For each Skill, sums the duration of every Experience that
uses that skill. Overlapping date ranges are not double-counted (intersection
is computed). Current experiences contribute up to the analysis date.

### total_years_of_experience

Computes the total professional experience duration.

**Input:** All experience nodes with dateRange properties.
**Output:** A Finding with the total years as a float.
**Behaviour:** Sums the durations of all experiences, subtracting
overlapping periods. Earliest start date to latest end date (or analysis date
for current experiences). Returns total in years with one decimal place.

### programming_language_evidence

Aggregates all programming language skills.

**Input:** Skill nodes with category = "Programming Language" (or equivalent).
**Output:** A Finding listing all programming languages with years of use and
recency.
**Behaviour:** Filters skills by programming language category. For each,
applies years_of_experience_per_skill and skill_recency. Returns a structured
list of languages with computed attributes.

### infrastructure_evidence

Aggregates all infrastructure and platform engineering evidence.

**Input:** Skill nodes with infrastructure-related categories (DevOps, IaC,
Cloud, Platform Engineering, SRE, CI/CD).
**Output:** A Finding summarising infrastructure capabilities.
**Behaviour:** Filters skills by infrastructure category keywords. Groups by
subdomain (cloud providers, container orchestration, CI/CD tools, monitoring,
IaC tools). Returns a structured summary with per-subdomain skill lists and
experience counts.

### security_evidence

Aggregates all security-related evidence.

**Input:** Skill nodes with security-related categories or names, experience
nodes with security-related scope references.
**Output:** A Finding describing security capabilities.
**Behaviour:** Matches skills against a security keyword set (security,
compliance, audit, threat, vulnerability, zero-trust, cryptography, IAM).
Also scans experience scopes for security-related responsibilities. Returns
a combined Finding with both explicit skills and scope-based evidence.

### cloud_expertise

Determines cloud platform proficiency.

**Input:** Skill nodes matching cloud provider names (AWS, Azure, GCP, etc.)
and related technologies (Kubernetes, Terraform, Serverless).
**Output:** A Finding listing cloud platforms with proficiency levels.
**Behaviour:** Matches skills against cloud provider names and related
technologies. Groups by provider. Applies years_of_experience_per_skill to
each group to determine depth.

---

## Rule Group: Education

### highest_education

Identifies the highest degree level attained.

**Input:** Education nodes with program and dateRange properties.
**Output:** A Finding with the highest degree and its institution.
**Behaviour:** Ranks education entries by degree level hierarchy (PhD > Master
> Bachelor > Associate > Diploma > Certificate). Returns the highest-ranked
entry. If multiple entries share the same level, the most recent is preferred.

### education_relevance

Determines how relevant the education is to the current career trajectory.

**Input:** Education nodes, Experience nodes with scope/technologies.
**Output:** A Finding scoring education-to-career alignment.
**Behaviour:** Compares the field of study against technologies used in recent
experiences. Direct field match = high relevance. Adjacent field = medium.
Unrelated field = low.

---

## Rule Group: Tenure

### years_per_organization

Computes tenure per organization.

**Input:** Experience nodes, AT_ORGANIZATION edges.
**Output:** Findings mapping each organization to total years worked.
**Behaviour:** For each Organization node, sums durations of all AT_ORGANIZATION
edges from Experience nodes. Returns a per-organization tenure breakdown.

### recurring_organizations

Detects organizations where the person has worked more than once.

**Input:** Experience nodes, AT_ORGANIZATION edges.
**Output:** A Finding listing organizations with multiple engagements.
**Behaviour:** Counts AT_ORGANIZATION edges per Organization. Organizations with
two or more distinct experiences are flagged as recurring. Each recurrence
includes the date ranges of each engagement.

### average_tenure_per_role

Computes the average duration spent per role or organization.

**Input:** All experience nodes with dateRange properties.
**Output:** A Finding with the average tenure in years.
**Behaviour:** Computes mean duration across all non-current experiences.
Current experiences are excluded from the average but reported separately.

---

## Rule Group: Analysis

### career_stage_classification

Classifies the professional into a career stage.

**Input:** total_years_of_experience Finding, strongest_experience Finding,
highest_education Finding.
**Output:** A Finding with the classified stage.
**Behaviour:** Uses total years and title level to classify: Entry (<2 years),
Early (2–5), Mid (5–10), Senior (10–15), Lead (15–20), Executive (20+). The
classification is advisory, not prescriptive.

### industry_coverage

Lists the industries represented in the experience history.

**Input:** Experience nodes with scope or organization properties.
**Output:** A Finding listing industries with per-industry experience count.
**Behaviour:** Maps organization names and experience scopes to industry
classifications. Requires an industry mapping table (organization name →
industry). Organizations not in the mapping are classified as "unknown."
