# CSKS Example Queries

**Milestone**: M1.23 — CSKS Developer Experience & Semantic Query Layer
(M1.24/M1.25 profile quality & resume generation queries added at the end)

Over 80 representative queries. Run them with:

```bash
careeros csks query "<question>"
# or via the API:
curl "http://localhost:8000/csks/query?q=<url-encoded question>"
```

## Entity lookup — components, rules, generators

1. `What is ProfileLoader?`
2. `Describe ProfileLoader.`
3. `Explain ProfileLoader.`
4. `Tell me about the ExportContract.`
5. `What is the TotalYearsExperienceRule?`
6. `What is the StrongestExperienceRule?`
7. `Show me the ArtifactGenerator.`
8. `Define MarkdownCVGenerator.`
9. `What is the EvidenceSelector?`
10. `What is the ReasoningEngine?`
11. `Explain how the SchemaLoader works.`

## Entity lookup — domains

12. `What is Profile Management?`
13. `What is the Knowledge Layer?`
14. `What is the Reasoning Engine?`
15. `What is Artifact Generation?`
16. `What is Schema Foundation?`
17. `What is CV Optimization?`
18. `What is Interview Intelligence?`
19. `What is the Acquisition domain?`

## Entity lookup — ADRs and milestones

20. `What is ADR-008?`
21. `What is ADR 003?`
22. `What is ADR003?`
23. `What is ADR-002?`
24. `What is M1.22?`
25. `What is M1.21?`
26. `What is M1.20?`

## Listing

27. `List domains.`
28. `List generators.`
29. `List API endpoints.`
30. `List reasoning rules.`
31. `List ADRs.`
32. `List milestones.`
33. `List schemas.`
34. `List tests.`
35. `List CLI commands.`
36. `List configurations.`
37. `Show all rules.`
38. `Enumerate all domains.`
39. `cli commands`
40. `endpoints for profiles`
41. `schema for skill`

## Dependency analysis

42. `What depends on ProfileLoader?`
43. `What depends on Profile Management?`
44. `Who uses the ExportContract?`
45. `What uses the ReasoningEngine?`
46. `What imports the KnowledgeGraph?`

## Reverse dependency

47. `What does ArtifactGenerator depend on?`
48. `What are the dependencies of ProfileLoader?`
49. `What does the EvidenceSelector depend on?`
50. `What are the imports of the SchemaLoader?`

## Impact analysis

51. `What breaks if I change ProfileLoader?`
52. `What would break if I refactor the ReasoningEngine?`
53. `What is the impact of modifying the EvidenceSelector?`
54. `What happens if I change the ExportContract?`

## Data flow

55. `How does artifact generation work?`
56. `Data flow for artifact generation`
57. `How is a CV generated?`
58. `Walk me through interview preparation.`
59. `Explain how artifact generation works.`
60. `Data flow for acquisition`
61. `Flow for reasoning`

## Search

62. `Search profile.`
63. `Search interview.`
64. `Search artifact.`
65. `find schema`
66. `search for rules`

```bash
careeros csks search profile
careeros csks search interview
careeros csks search artifact
careeros csks search rule
```

## Capability checks

67. `Does CareerOS support PDF generation?`
68. `Does CSKS support LLM integration?`
69. `Does CareerOS support AI?`
70. `Can CareerOS generate DOCX artifacts?`
71. `Does CSKS support incremental indexing?`

## Status checks

72. `M1.22 status`
73. `M1.21 status`
74. `M1.20 status`

## Profile quality & resume generation

Resume-generation queries are answered from the canonical profile attached to
the query engine (via `CSKSQueryEngine(graph, profile=...)`). Health and
improvement answers are deterministic output of the Profile Quality Engine;
stale-artifact answers read the artifact lifecycle state written by the
Resolution Engine.

75. `What is my resume health?`
76. `What is my profile health?`
77. `How healthy is my resume?`
78. `Why isn't my profile 100% healthy?`
79. `List improvements`
80. `List improvements for my profile`
81. `What recommendations for my resume?`
82. `What should I fix in my profile?`
83. `Show duplicate narrative`
84. `Show duplicate narratives`
85. `What are the duplicate narratives?`
86. `Show stale artifacts`
87. `Which artifacts are stale?`
88. `What artifacts need regeneration?`

## Unknown / suggestions

`potato potato`

## JSON output

```bash
careeros csks query "What is ADR-008?" --json
```
