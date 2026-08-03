from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(slots=True)
class PersonData:
    id: str
    first_name: str
    last_name: str
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None


@dataclass(slots=True)
class ExperienceData:
    id: str
    organization: str
    title: str
    employment_type: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: Optional[bool] = None
    summary: Optional[str] = None
    responsibilities: list[str] = field(default_factory=list)
    achievements: list[str] = field(default_factory=list)
    technologies: list[str] = field(default_factory=list)
    source_ref: Optional[str] = None


@dataclass(slots=True)
class SkillData:
    name: str
    category: Optional[str] = None
    proficiency: Optional[str] = None
    evidence: list[dict] = field(default_factory=list)
    confidence: float = 0.0
    source_reference: Optional[str] = None


@dataclass(slots=True)
class EducationData:
    institution: str
    degree: str
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: Optional[bool] = None
    location: Optional[str] = None
    description: Optional[str] = None
    confidence: float = 0.0
    source_reference: Optional[str] = None


@dataclass(slots=True)
class ExtractionResult:
    person: PersonData
    experiences: list[ExperienceData] = field(default_factory=list)
    skills: list[SkillData] = field(default_factory=list)
    education: list[EducationData] = field(default_factory=list)
    confidence: float = 0.0
    warnings: list[str] = field(default_factory=list)
    source_document: Optional[str] = None
    extraction_timestamp: Optional[str] = None
