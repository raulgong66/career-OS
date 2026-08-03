from __future__ import annotations

import re
from typing import Any

CLOUD_PROVIDERS: dict[str, tuple[str, ...]] = {
    "AWS": (
        "aws",
        "amazon web services",
        "ec2",
        "s3",
        "lambda",
        "cloudformation",
        "eks",
        "ecs",
        "rds",
        "dynamodb",
        "cloudwatch",
        "iam",
        "route53",
        "elasticache",
        "sqs",
        "sns",
    ),
    "Azure": (
        "azure",
        "microsoft azure",
        "azure devops",
        "azure functions",
        "azure storage",
        "azure sql",
        "aad",
        "entra",
    ),
    "GCP": (
        "gcp",
        "google cloud",
        "google cloud platform",
        "bigquery",
        "gke",
        "cloud storage",
        "cloud functions",
        "dataflow",
    ),
}

INDUSTRIES: dict[str, tuple[str, ...]] = {
    "Finance": (
        "finance",
        "bank",
        "financial",
        "fintech",
        "insurance",
        "investment",
        "payments",
        "credit",
        "wealth",
        "capital",
        "trading",
    ),
    "Healthcare": (
        "healthcare",
        "health",
        "medical",
        "hospital",
        "pharma",
        "clinical",
        "biotech",
        "life sciences",
    ),
    "Telecom": (
        "telecom",
        "telecommunications",
        "mobile network",
        "isp",
        "wireless",
        "broadband",
    ),
    "Retail": (
        "retail",
        "ecommerce",
        "e-commerce",
        "consumer goods",
        "omnichannel",
    ),
    "Government": (
        "government",
        "public sector",
        "federal",
        "state agency",
        "defense",
        "municipal",
        "civic",
    ),
    "Manufacturing": (
        "manufacturing",
        "industrial",
        "supply chain",
        "logistics",
        "automotive",
        "factory",
    ),
    "Consulting": (
        "consulting",
        "consultancy",
        "professional services",
        "advisory",
    ),
    "Technology": (
        "technology",
        "software",
        "saas",
        "cloud",
        "platform",
        "tech",
        "digital",
    ),
    "Education": (
        "education",
        "edtech",
        "university",
        "academic",
        "training",
        "e-learning",
    ),
    "Energy": (
        "energy",
        "utilities",
        "oil and gas",
        "renewable",
        "power",
        "petroleum",
    ),
}

LEADERSHIP_KEYWORDS: dict[str, int] = {
    "team lead": 1,
    "technical lead": 1,
    "tech lead": 1,
    "architect": 2,
    "manager": 2,
    "managing": 2,
    "director": 3,
    "principal": 3,
    "cto": 4,
    "vice president": 4,
    "chief": 4,
    "head of": 3,
    "vp": 4,
    "lead": 1,
}

RESPONSIBILITY_AREAS: dict[str, tuple[str, ...]] = {
    "architecture": (
        "architect",
        "architecture",
        "system design",
        "solution design",
        "technical design",
    ),
    "devops": (
        "devops",
        "ci/cd",
        "jenkins",
        "github actions",
        "gitlab ci",
        "deployment",
        "infrastructure as code",
        "terraform",
        "ansible",
        "pipeline",
    ),
    "platform_ownership": (
        "platform owner",
        "platform engineer",
        "platform team",
        "internal platform",
        "developer experience",
    ),
    "migrations": (
        "migration",
        "migrate",
        "cloud migration",
        "data migration",
        "legacy modernization",
        "lift and shift",
        "digital transformation",
    ),
    "security": (
        "security",
        "cybersecurity",
        "security engineer",
        "application security",
        "appsec",
        "compliance",
        "vulnerability",
    ),
    "operations": (
        "operations",
        "site reliability",
        "sre",
        "incident response",
        "on-call",
        "production support",
        "reliability",
    ),
    "mentoring": (
        "mentor",
        "mentoring",
        "coach",
        "technical lead",
        "team lead",
        "people management",
    ),
}

MIGRATION_KEYWORDS: tuple[str, ...] = (
    "migration",
    "migrate",
    "cloud migration",
    "data migration",
    "legacy modernization",
    "lift and shift",
    "digital transformation",
)


def word_boundary_match(word: str, text: str) -> bool:
    lower_word = word.lower()
    lower_text = text.lower()
    if " " in lower_word:
        return lower_word in lower_text
    return bool(re.search(rf"\b{re.escape(lower_word)}\b", lower_text))


def detect_cloud_provider(skill_name: str) -> str | None:
    lower = skill_name.lower()
    for provider, keywords in CLOUD_PROVIDERS.items():
        for kw in keywords:
            if word_boundary_match(kw, lower):
                return provider
    return None


def detect_industry(
    org_name: str, title: str = "", scope: str = ""
) -> str | None:
    combined = f"{org_name} {title} {scope}".lower()
    for industry, keywords in INDUSTRIES.items():
        for kw in keywords:
            if kw in combined:
                return industry
    return None


def detect_leadership_role(title: str) -> str | None:
    lower = title.lower()
    for keyword in LEADERSHIP_KEYWORDS:
        if word_boundary_match(keyword, lower):
            return keyword
    return None


def detect_responsibility_areas(
    title: str, scope: str = ""
) -> dict[str, list[str]]:
    combined = f"{title} {scope}".lower()
    result: dict[str, list[str]] = {}
    for area, keywords in RESPONSIBILITY_AREAS.items():
        matches = [kw for kw in keywords if kw in combined or word_boundary_match(kw, combined)]
        if matches:
            result[area] = matches
    return result


def has_migration_keywords(title: str, scope: str = "") -> bool:
    combined = f"{title} {scope}".lower()
    for kw in MIGRATION_KEYWORDS:
        if kw in combined:
            return True
    return False
