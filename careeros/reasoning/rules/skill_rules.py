from __future__ import annotations

from datetime import datetime
from typing import Any

from careeros.evidence_hydration import (
    compute_evidence_strength,
    derive_skill_evidence_confidence,
    evidence_confidence_meta,
    evidence_strength_label,
)
from careeros.reasoning import ReasoningResult, Rule, RuleContext
from careeros.reasoning.utils import (
    duration_years,
    parse_date_range,
    reference_now,
    word_boundary_match,
)


# ---------------------------------------------------------------------------
# Shared lookup tables
# ---------------------------------------------------------------------------

SKILL_CATEGORIES: dict[str, tuple[str, ...]] = {
    "Programming": (
        "python", "java", "javascript", "typescript", "go", "rust",
        "c#", "c++", "c", "ruby", "php", "swift", "kotlin", "scala",
        "perl", "r", "dart", "lua", "shell", "bash", "powershell",
        "sql", "pl/sql", "html", "css", "sass", "less",
    ),
    "Cloud": (
        "aws", "azure", "gcp", "amazon web services", "google cloud",
        "cloudformation", "terraform", "pulumi", "ec2", "s3", "lambda",
        "eks", "ecs", "gke", "aks", "rds", "dynamodb", "cloudwatch",
        "cloudfront", "route53", "iam", "vpc",
    ),
    "DevOps": (
        "docker", "kubernetes", "jenkins", "gitlab ci", "github actions",
        "circleci", "ansible", "chef", "puppet", "helm", "argocd",
        "flux", "spinnaker", "teamcity", "bamboo", "travis ci",
        "devops", "ci/cd", "containerization", "orchestration",
    ),
    "Databases": (
        "postgresql", "postgres", "mysql", "mongodb", "redis",
        "elasticsearch", "cassandra", "oracle", "sql server", "sqlite",
        "mariadb", "couchdb", "neo4j", "influxdb", "timescaledb",
        "bigquery", "redshift", "snowflake",
    ),
    "Architecture": (
        "microservices", "event-driven", "domain-driven design",
        "rest", "graphql", "grpc", "event sourcing", "cqrs",
        "system design", "solution architecture",
    ),
    "Leadership": (
        "team leadership", "people management", "project management",
        "product management", "scrum", "agile", "stakeholder",
        "mentoring", "coaching",
    ),
    "Security": (
        "security", "cybersecurity", "penetration testing",
        "vulnerability", "compliance", "oauth", "saml",
        "openid connect", "tls", "encryption", "appsec", "devsecops",
    ),
    "Testing": (
        "pytest", "junit", "selenium", "cypress", "playwright",
        "jest", "mocha", "testing", "tdd", "unit testing",
        "integration testing", "e2e testing",
    ),
    "Monitoring": (
        "prometheus", "grafana", "datadog", "new relic", "splunk",
        "elk", "elastic stack", "jaeger", "opentelemetry",
    ),
}

RARE_SKILLS: tuple[str, ...] = (
    "mainframe", "cobol", "fortran", "assembly", "vhdl", "verilog",
    "ada", "lisp", "prolog", "haskell", "erlang", "smalltalk",
    "objective-c", "coldfusion", "apex", "abap", "sap", "pega",
    "sas", "spss", "matlab", "labview", "autocad", "solidworks",
    "ansys", "cuda", "opencl", "fpga", "zos", "z/os", "ibm i",
    "as/400", "rpg", "blockchain", "solidity", "qiskit",
    "embedded", "rtos", "vxworks",
)

SPECIALIZED_SKILLS: tuple[str, ...] = (
    "kubernetes", "k8s", "terraform", "opentelemetry", "zero trust",
    "iam", "vmware", "kafka", "istio", "linkerd", "envoy",
    "prometheus", "grafana", "datadog", "new relic", "splunk",
    "elasticsearch", "kibana", "logstash", "nginx", "traefik",
    "consul", "vault", "nomad", "packer", "vagrant",
    "ansible", "chef", "puppet", "saltstack",
    "terraform cloud", "terragrunt", "crossplane",
    "argocd", "flux", "helm", "kustomize",
    "gitlab ci", "github actions", "circleci", "jenkins",
    "sonarqube", "sonarcloud", "snyk", "trivy",
    "opa", "open policy agent", "kyverno",
    "cockroachdb", "cassandra", "couchbase", "dynamodb",
    "redis", "memcached", "rabbitmq", "nats", "pulsar",
    "graphql", "grpc", "protobuf", "avro", "thrift",
    "react", "angular", "vue", "svelte", "nextjs", "nuxt",
    "django", "spring", "rails", "laravel", "asp.net",
    "pytorch", "tensorflow", "scikit-learn", "mlflow",
    "airflow", "dagster", "prefect", "spark", "flink",
    "databricks", "snowflake", "bigquery", "redshift",
    "tableau", "power bi", "looker", "qlik",
    "sap", "oracle", "pega", "servicenow",
    "salesforce", "hubspot", "marketo",
    "okta", "auth0", "entra", "azure ad",
    "cloudflare", "akamai", "fastly",
    "datadog", "dynatrace", "appdynamics",
    "splunk", "sumo logic", "elastic",
    "pagerduty", "opsgenie", "victorops",
)

TRANSFERABLE_SKILLS: tuple[str, ...] = (
    "leadership", "team leadership", "people management",
    "project management", "communication", "stakeholder management",
    "mentoring", "coaching", "architecture", "system design",
    "solution architecture", "automation", "platform engineering",
    "devops", "problem solving", "critical thinking", "analytical",
    "agile", "scrum", "cross-functional", "technical writing",
    "presentation", "public speaking", "negotiation",
    "strategic planning", "risk management", "change management",
    "incident response", "reliability", "sre", "site reliability",
    "api design",
)

PROFICIENCY_LEVELS: dict[str, int] = {
    "beginner": 1,
    "novice": 1,
    "elementary": 1,
    "intermediate": 2,
    "proficient": 3,
    "advanced": 4,
    "expert": 5,
}


def _categorize_skill(skill_name: str) -> str | None:
    lower = skill_name.lower()
    for category, keywords in SKILL_CATEGORIES.items():
        for kw in keywords:
            if word_boundary_match(kw, lower):
                return category
    return None


def _is_rare_skill(skill_name: str) -> bool:
    lower = skill_name.lower()
    for kw in RARE_SKILLS:
        if word_boundary_match(kw, lower):
            return True
    return False


def _is_transferable_skill(skill_name: str) -> bool:
    lower = skill_name.lower()
    for kw in TRANSFERABLE_SKILLS:
        if word_boundary_match(kw, lower):
            return True
    return False


def _is_specialized_skill(skill_name: str) -> bool:
    lower = skill_name.lower()
    for kw in SPECIALIZED_SKILLS:
        if word_boundary_match(kw, lower):
            return True
    return False


def _resolve_proficiency(proficiency: str | None) -> int:
    if not proficiency:
        return 2
    lower = proficiency.strip().lower()
    return PROFICIENCY_LEVELS.get(lower, 2)


def _collect_skill_data(context: RuleContext) -> list[dict[str, Any]]:
    skills: list[dict[str, Any]] = []
    for skill_node in context.graph.skills():
        name = skill_node.label
        props = skill_node.properties
        raw_category = props.get("category", "")
        category = raw_category if raw_category else _categorize_skill(name)
        proficiency = _resolve_proficiency(props.get("proficiency"))

        exp_nodes = context.graph.experiences_using(name)
        org_nodes = context.graph.organizations_for_skill(name)

        exp_ids: set[str] = set()
        yr_total = 0.0
        earliest: datetime | None = None
        latest: datetime | None = None
        exp_details: list[dict[str, Any]] = []

        for exp_node in exp_nodes:
            eid = exp_node.id
            if eid in exp_ids:
                continue
            exp_ids.add(eid)
            eprops = exp_node.properties
            dr = parse_date_range({
                "start": eprops.get("startDate"),
                "end": eprops.get("endDate"),
                "isCurrent": eprops.get("isCurrent", False),
            })
            dur = duration_years(dr)
            yr_total += dur

            if dr.start and (earliest is None or dr.start < earliest):
                earliest = dr.start
            end = dr.end if dr.end is not None else reference_now()
            if latest is None or end > latest:
                latest = end

            exp_details.append({
                "id": eid,
                "title": eprops.get("title", ""),
                "duration_years": round(dur, 2),
            })

        org_names = sorted(set(n.label for n in org_nodes))

        skills.append({
            "id": skill_node.id,
            "name": name,
            "category": category,
            "proficiency": proficiency,
            "experience_count": len(exp_ids),
            "organization_count": len(org_names),
            "organizations": org_names,
            "total_years": round(yr_total, 2),
            "earliest_use": earliest.isoformat() if earliest else None,
            "most_recent_use": latest.isoformat() if latest else None,
            "experiences": exp_details,
        })
    return skills


# ---------------------------------------------------------------------------
# 1. StrongestSkillsRule
# ---------------------------------------------------------------------------


class StrongestSkillsRule(Rule):
    id = "strongest_skills"
    name = "Strongest Skills"
    description = (
        "Ranks skills by evidence strength: years of use, number of experiences, "
        "recency, and proficiency level"
    )

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        skill_data = _collect_skill_data(context)
        ranked = self._rank_skills(skill_data)

        return [
            ReasoningResult(
                rule_id=self.id,
                finding_type="strongest_skills",
                value=ranked,
                confidence=1.0,
                evidence_refs=tuple(s["id"] for s in skill_data if s["id"]),
                metadata={
                    "total_skills_analyzed": len(skill_data),
                    "top_skill": ranked[0]["name"] if ranked else "",
                    "top_score": round(ranked[0]["score"], 4) if ranked else 0.0,
                },
            )
        ]

    @staticmethod
    def _rank_skills(skill_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        scored: list[dict[str, Any]] = []
        for s in skill_data:
            years_score = min(s["total_years"] / 10.0, 1.0) * 0.35
            exp_count_score = min(s["experience_count"] / 5.0, 1.0) * 0.25
            prof_score = (s["proficiency"] / 5.0) * 0.20
            org_score = min(s["organization_count"] / 3.0, 1.0) * 0.20
            total = years_score + exp_count_score + prof_score + org_score

            scored.append({
                "name": s["name"],
                "category": s["category"],
                "score": round(total, 4),
                "total_years": s["total_years"],
                "experience_count": s["experience_count"],
                "organization_count": s["organization_count"],
                "proficiency": s["proficiency"],
                "most_recent_use": s["most_recent_use"],
            })

        scored.sort(key=lambda x: (-x["score"], -x["total_years"], x["name"]))
        return scored


# ---------------------------------------------------------------------------
# 2. EmergingSkillsRule
# ---------------------------------------------------------------------------


class EmergingSkillsRule(Rule):
    id = "emerging_skills"
    name = "Emerging Skills"
    description = (
        "Detects recently acquired skills with limited historical experience "
        "but recent evidence of use"
    )

    EMERGING_YEARS_THRESHOLD = 2.0

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        skill_data = _collect_skill_data(context)
        now = reference_now()
        emerging: list[dict[str, Any]] = []

        for s in skill_data:
            if s["earliest_use"] is None:
                continue
            first = datetime.fromisoformat(s["earliest_use"])
            years_since_first = duration_years(
                parse_date_range({"start": first.isoformat(), "end": now.isoformat()})
            )
            if years_since_first <= self.EMERGING_YEARS_THRESHOLD:
                emerging.append({
                    "name": s["name"],
                    "category": s["category"],
                    "first_used": s["earliest_use"],
                    "most_recent_use": s["most_recent_use"],
                    "total_years": s["total_years"],
                    "experience_count": s["experience_count"],
                })

        emerging.sort(key=lambda x: (-x["experience_count"], x["name"]))

        return [
            ReasoningResult(
                rule_id=self.id,
                finding_type="emerging_skills",
                value=emerging,
                confidence=1.0,
                evidence_refs=tuple(s["id"] for s in skill_data if s["id"]
                                     and any(e["name"] == s["name"] for e in emerging)),
                metadata={
                    "emerging_count": len(emerging),
                    "threshold_years": self.EMERGING_YEARS_THRESHOLD,
                    "total_skills_analyzed": len(skill_data),
                },
            )
        ]


# ---------------------------------------------------------------------------
# 3. CoreCompetenciesRule
# ---------------------------------------------------------------------------


class CoreCompetenciesRule(Rule):
    id = "core_competencies"
    name = "Core Competencies"
    description = (
        "Identifies long-term core competencies characterised by repeated "
        "evidence, multiple employers, and sustained use"
    )

    MIN_CORE_YEARS = 2.0
    MIN_CORE_EMPLOYERS = 1

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        skill_data = _collect_skill_data(context)
        core: list[dict[str, Any]] = []

        for s in skill_data:
            if s["total_years"] < self.MIN_CORE_YEARS:
                continue
            if s["organization_count"] < self.MIN_CORE_EMPLOYERS:
                continue

            breadth = "single_employer" if s["organization_count"] <= 1 else "multi_employer"
            depth = "sustained" if s["total_years"] >= 4.0 else "developing"

            core.append({
                "name": s["name"],
                "category": s["category"],
                "total_years": s["total_years"],
                "experience_count": s["experience_count"],
                "organization_count": s["organization_count"],
                "breadth": breadth,
                "depth": depth,
            })

        core.sort(key=lambda x: (-x["total_years"], -x["experience_count"], x["name"]))

        return [
            ReasoningResult(
                rule_id=self.id,
                finding_type="core_competencies",
                value=core,
                confidence=1.0,
                evidence_refs=tuple(s["id"] for s in skill_data if s["id"]),
                metadata={
                    "core_count": len(core),
                    "min_years": self.MIN_CORE_YEARS,
                    "total_skills_analyzed": len(skill_data),
                },
            )
        ]


# ---------------------------------------------------------------------------
# 4. SkillCategoryBalanceRule
# ---------------------------------------------------------------------------


class SkillCategoryBalanceRule(Rule):
    id = "skill_category_balance"
    name = "Skill Category Balance"
    description = (
        "Analyses skill distribution across categories to determine "
        "strongest and weakest areas"
    )

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        skill_data = _collect_skill_data(context)

        category_stats: dict[str, dict[str, Any]] = {}
        for s in skill_data:
            cat = s["category"] or "Uncategorized"
            if cat not in category_stats:
                category_stats[cat] = {
                    "count": 0,
                    "total_years": 0.0,
                    "experience_count": 0,
                    "skills": [],
                }
            category_stats[cat]["count"] += 1
            category_stats[cat]["total_years"] += s["total_years"]
            category_stats[cat]["experience_count"] += s["experience_count"]
            category_stats[cat]["skills"].append(s["name"])

        for stats in category_stats.values():
            stats["total_years"] = round(stats["total_years"], 1)
            stats["skills"].sort()

        categories_sorted = sorted(category_stats.keys())
        strongest: str | None = None
        weakest: str | None = None
        if categories_sorted:
            strongest = max(categories_sorted, key=lambda c: category_stats[c]["count"])
            weakest = min(categories_sorted, key=lambda c: category_stats[c]["count"])

        total_count = len(skill_data)
        balance_metric = 1.0
        if total_count > 0 and category_stats:
            max_count = max(cs["count"] for cs in category_stats.values())
            min_count = min(cs["count"] for cs in category_stats.values())
            range_val = max_count - min_count
            balance_metric = round(1.0 - (range_val / max(1, max_count)), 2)

        return [
            ReasoningResult(
                rule_id=self.id,
                finding_type="skill_category_balance",
                value={
                    "categories": category_stats,
                    "strongest_category": strongest,
                    "weakest_category": weakest,
                    "balance_metric": balance_metric,
                    "total_categories": len(category_stats),
                },
                confidence=1.0,
                evidence_refs=tuple(s["id"] for s in skill_data if s["id"]),
                metadata={
                    "category_count": len(category_stats),
                    "strongest": strongest or "",
                    "weakest": weakest or "",
                },
            )
        ]


# ---------------------------------------------------------------------------
# 5. SkillEvidenceStrengthRule
# ---------------------------------------------------------------------------


class SkillEvidenceStrengthRule(Rule):
    id = "skill_evidence_strength"
    name = "Skill Evidence Strength"
    description = (
        "Measures evidence quality for each skill, producing deterministic "
        "confidence values based on experience breadth and depth"
    )

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        skill_data = _collect_skill_data(context)
        strengths: list[dict[str, Any]] = []

        for s in skill_data:
            confidence = self._compute_confidence(s)
            label = self._confidence_to_label(confidence)

            strengths.append({
                "name": s["name"],
                "category": s["category"],
                "confidence": confidence,
                "label": label,
                "experience_count": s["experience_count"],
                "organization_count": s["organization_count"],
                "total_years": s["total_years"],
            })

        strengths.sort(key=lambda x: (-x["confidence"], -x["total_years"], x["name"]))

        metadata = {
            "total_skills_analyzed": len(skill_data),
            "high_confidence_count": sum(
                1 for s in strengths if s["label"] == "very_high"
            ),
        }
        metadata.update(evidence_confidence_meta(skill_data, context.profile))

        return [
            ReasoningResult(
                rule_id=self.id,
                finding_type="skill_evidence_strength",
                value=strengths,
                confidence=derive_skill_evidence_confidence(
                    skill_data, context.profile
                ),
                evidence_refs=tuple(s["id"] for s in skill_data if s["id"]),
                metadata=metadata,
            )
        ]

    @staticmethod
    def _compute_confidence(skill: dict[str, Any]) -> float:
        """Evidence-strength confidence (reused shared implementation)."""
        return compute_evidence_strength(skill)

    @staticmethod
    def _confidence_to_label(confidence: float) -> str:
        """Evidence-strength band label (reused shared implementation)."""
        return evidence_strength_label(confidence)


# ---------------------------------------------------------------------------
# 6. RareSkillsRule
# ---------------------------------------------------------------------------


class RareSkillsRule(Rule):
    id = "rare_skills"
    name = "Rare Skills"
    description = "Identifies uncommon or highly specialised skills using configurable lookup tables"

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        skill_data = _collect_skill_data(context)
        rare: list[dict[str, Any]] = []

        for s in skill_data:
            if _is_rare_skill(s["name"]):
                rare.append({
                    "name": s["name"],
                    "category": s["category"],
                    "experience_count": s["experience_count"],
                    "total_years": s["total_years"],
                })

        rare.sort(key=lambda x: (-x["experience_count"], x["name"]))

        return [
            ReasoningResult(
                rule_id=self.id,
                finding_type="rare_skills",
                value=rare,
                confidence=1.0,
                evidence_refs=tuple(s["id"] for s in skill_data if s["id"]
                                     and any(r["name"] == s["name"] for r in rare)),
                metadata={
                    "rare_count": len(rare),
                    "total_skills_analyzed": len(skill_data),
                },
            )
        ]


# ---------------------------------------------------------------------------
# 7. SpecializedSkillsRule
# ---------------------------------------------------------------------------


class SpecializedSkillsRule(Rule):
    id = "specialized_skills"
    name = "Specialized Skills"
    description = (
        "Identifies highly specialised technical capabilities using "
        "a configurable deterministic lookup table"
    )

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        skill_data = _collect_skill_data(context)
        specialized: list[dict[str, Any]] = []

        for s in skill_data:
            if _is_specialized_skill(s["name"]):
                specialized.append({
                    "name": s["name"],
                    "category": s["category"],
                    "experience_count": s["experience_count"],
                    "organization_count": s["organization_count"],
                    "total_years": s["total_years"],
                })

        specialized.sort(key=lambda x: (-x["total_years"], -x["experience_count"], x["name"]))

        return [
            ReasoningResult(
                rule_id=self.id,
                finding_type="specialized_skills",
                value=specialized,
                confidence=1.0,
                evidence_refs=tuple(s["id"] for s in skill_data if s["id"]
                                     and any(sp["name"] == s["name"] for sp in specialized)),
                metadata={
                    "specialized_count": len(specialized),
                    "total_skills_analyzed": len(skill_data),
                },
            )
        ]


# ---------------------------------------------------------------------------
# 8. TransferableSkillsRule
# ---------------------------------------------------------------------------


class TransferableSkillsRule(Rule):
    id = "transferable_skills"
    name = "Transferable Skills"
    description = (
        "Identifies skills applicable across industries or roles "
        "such as leadership, architecture, automation, and communication"
    )

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        skill_data = _collect_skill_data(context)
        transferable: list[dict[str, Any]] = []

        for s in skill_data:
            if _is_transferable_skill(s["name"]):
                transferable.append({
                    "name": s["name"],
                    "category": s["category"],
                    "experience_count": s["experience_count"],
                    "organization_count": s["organization_count"],
                    "total_years": s["total_years"],
                })

        transferable.sort(key=lambda x: (-x["total_years"], -x["experience_count"], x["name"]))

        return [
            ReasoningResult(
                rule_id=self.id,
                finding_type="transferable_skills",
                value=transferable,
                confidence=1.0,
                evidence_refs=tuple(s["id"] for s in skill_data if s["id"]
                                     and any(t["name"] == s["name"] for t in transferable)),
                metadata={
                    "transferable_count": len(transferable),
                    "total_skills_analyzed": len(skill_data),
                },
            )
        ]


# ---------------------------------------------------------------------------
# 8. SkillProgressionRule
# ---------------------------------------------------------------------------


class SkillProgressionRule(Rule):
    id = "skill_progression"
    name = "Skill Progression"
    description = (
        "Detects professional progression based on accumulated skill evidence, "
        "identifying career stage transitions"
    )

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        skill_data = _collect_skill_data(context)
        profile = context.profile

        total_skills = len(skill_data)
        multi_exp_skills = sum(1 for s in skill_data if s["experience_count"] >= 2)
        multi_org_skills = sum(1 for s in skill_data if s["organization_count"] >= 2)
        sustained_skills = sum(1 for s in skill_data if s["total_years"] >= 3.0)
        avg_years = (
            round(sum(s["total_years"] for s in skill_data) / max(1, total_skills), 1)
        )

        max_tl = 2
        for exp in profile.get("experiences", []):
            title = exp.get("title", "")
            from careeros.reasoning.utils import title_level
            tl = title_level(title)
            if tl > max_tl:
                max_tl = tl

        avg_proficiency = (
            round(sum(s["proficiency"] for s in skill_data) / max(1, total_skills), 1)
        )

        stage = self._classify_progression(
            total_skills=total_skills,
            multi_exp_skills=multi_exp_skills,
            multi_org_skills=multi_org_skills,
            sustained_skills=sustained_skills,
            avg_years=avg_years,
            max_title_level=max_tl,
            avg_proficiency=avg_proficiency,
        )

        return [
            ReasoningResult(
                rule_id=self.id,
                finding_type="skill_progression",
                value={
                    "stage": stage,
                    "total_skills": total_skills,
                    "multi_experience_skills": multi_exp_skills,
                    "multi_organization_skills": multi_org_skills,
                    "sustained_skills": sustained_skills,
                    "average_skill_years": avg_years,
                    "average_proficiency": avg_proficiency,
                    "highest_title_level": max_tl,
                },
                confidence=1.0,
                evidence_refs=tuple(s["id"] for s in skill_data if s["id"]),
                metadata={
                    "stage": stage,
                    "total_skills": total_skills,
                },
            )
        ]

    @staticmethod
    def _classify_progression(
        total_skills: int,
        multi_exp_skills: int,
        multi_org_skills: int,
        sustained_skills: int,
        avg_years: float,
        max_title_level: int,
        avg_proficiency: float,
    ) -> str:
        depth_score = 0
        if total_skills >= 10:
            depth_score += 2
        elif total_skills >= 5:
            depth_score += 1
        if multi_exp_skills >= 3:
            depth_score += 2
        elif multi_exp_skills >= 1:
            depth_score += 1
        if multi_org_skills >= 2:
            depth_score += 2
        elif multi_org_skills >= 1:
            depth_score += 1
        if sustained_skills >= 3:
            depth_score += 2
        elif sustained_skills >= 1:
            depth_score += 1
        if avg_years >= 4.0:
            depth_score += 2
        elif avg_years >= 2.0:
            depth_score += 1
        if max_title_level >= 4:
            depth_score += 2
        elif max_title_level >= 3:
            depth_score += 1
        if avg_proficiency >= 4.0:
            depth_score += 2
        elif avg_proficiency >= 3.0:
            depth_score += 1

        if depth_score >= 10:
            return "expert"
        if depth_score >= 7:
            return "advanced"
        if depth_score >= 4:
            return "intermediate"
        return "foundation"
