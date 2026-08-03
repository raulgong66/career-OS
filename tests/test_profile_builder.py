from careeros.acquisition.builders import EducationBuilder, ExperienceBuilder, SkillBuilder, INSTITUTION_ALIASES
from careeros.acquisition.builders.base import BuilderRegistry
from careeros.acquisition.person_data import EducationData, ExperienceData, ExtractionResult, PersonData, SkillData
from careeros.acquisition.profile_builder import CanonicalProfileBuilder
from careeros.acquisition.utils import normalize_company, normalize_date


def test_build_creates_valid_structure() -> None:
    person = PersonData(
        id="person-test",
        first_name="Jane",
        last_name="Doe",
        full_name="Jane Doe",
        email="jane@example.com",
        phone="+1-555-0100",
        location="Stockholm, Sweden",
        linkedin="https://linkedin.com/in/janedoe",
        github="https://github.com/janedoe",
    )
    builder = CanonicalProfileBuilder()
    profile = builder.build(person)

    assert profile["profileVersion"] == "1.0.0"
    assert profile["person"]["id"] == "person-test"
    assert profile["person"]["names"] == [{"value": "Jane Doe", "usage": "professional"}]
    assert profile["person"]["contact"]["email"] == "jane@example.com"
    assert profile["person"]["contact"]["phone"] == "+1-555-0100"
    assert profile["person"]["location"]["label"] == "Stockholm, Sweden"
    assert profile["person"]["links"][0]["label"] == "LinkedIn"
    assert profile["person"]["links"][0]["href"] == "https://linkedin.com/in/janedoe"
    assert profile["person"]["links"][1]["label"] == "GitHub"
    assert profile["person"]["links"][1]["href"] == "https://github.com/janedoe"
    assert profile["professionalSummaries"] == []
    assert profile["experiences"] == []
    assert profile["skills"] == []


def test_build_handles_minimal_person() -> None:
    person = PersonData(
        id="person-min",
        first_name="Bob",
        last_name="Smith",
        full_name="Bob Smith",
    )
    builder = CanonicalProfileBuilder()
    profile = builder.build(person)

    assert profile["person"]["id"] == "person-min"
    assert "contact" not in profile["person"]
    assert "location" not in profile["person"]
    assert "links" not in profile["person"]


def test_build_omits_empty_optional_fields() -> None:
    person = PersonData(
        id="person-opt",
        first_name="Alice",
        last_name="Jones",
        full_name="Alice Jones",
        email="alice@example.com",
    )
    builder = CanonicalProfileBuilder()
    profile = builder.build(person)

    assert profile["person"]["contact"]["email"] == "alice@example.com"
    assert "phone" not in profile["person"]["contact"]
    assert "links" not in profile["person"]


def test_build_experience_happy_path() -> None:
    person = PersonData(id="person-test", first_name="J", last_name="D", full_name="J D")
    experiences = [
        ExperienceData(
            id="exp-swe-ab",
            organization="AB Corp",
            title="Software Engineer",
            employment_type="Full-time",
            location="Stockholm",
            start_date="2022-03",
            end_date="2025-01",
            is_current=False,
            summary="Full stack developer",
            responsibilities=["Built APIs", "Wrote tests"],
            achievements=["Increased perf 2x"],
            technologies=["Python", "Postgres"],
            source_ref="resume.pdf",
        ),
    ]
    builder = CanonicalProfileBuilder()
    profile = builder.build(person, experiences)

    assert len(profile["experiences"]) == 1
    exp = profile["experiences"][0]
    assert exp["id"] == "exp-swe-ab"
    assert exp["title"] == "Software Engineer"
    assert exp["organizationRefs"] == [{"id": "org-ab-corp", "type": "organization"}]
    assert exp["dateRange"]["start"] == "2022-03"
    assert exp["dateRange"]["end"] == "2025-01"
    assert exp["dateRange"]["isCurrent"] is False
    assert exp["location"]["label"] == "Stockholm"
    assert exp["engagementType"] == "Full-time"
    assert exp["scope"] == "Full stack developer"

    assert len(profile["organizations"]) == 1
    org = profile["organizations"][0]
    assert org["id"] == "org-ab-corp"
    assert org["name"] == "AB Corp"


def test_build_experience_current_detection() -> None:
    person = PersonData(id="person-test", first_name="J", last_name="D", full_name="J D")
    experiences = [
        ExperienceData(
            id="exp-current",
            organization="Current Inc",
            title="Senior Dev",
            start_date="2023-06",
            is_current=True,
        ),
    ]
    builder = CanonicalProfileBuilder()
    profile = builder.build(person, experiences)

    exp = profile["experiences"][0]
    assert exp["dateRange"]["start"] == "2023-06"
    assert "end" not in exp["dateRange"]
    assert exp["dateRange"]["isCurrent"] is True


def test_build_experience_no_date_normalized_is_current() -> None:
    person = PersonData(id="person-test", first_name="J", last_name="D", full_name="J D")
    experiences = [
        ExperienceData(
            id="exp-now",
            organization="Now Inc",
            title="Current Role",
        ),
    ]
    builder = CanonicalProfileBuilder()
    profile = builder.build(person, experiences)

    exp = profile["experiences"][0]
    assert exp["dateRange"]["isCurrent"] is True


def test_build_experience_deduplication() -> None:
    person = PersonData(id="person-test", first_name="J", last_name="D", full_name="J D")
    experiences = [
        ExperienceData(
            id="exp-a",
            organization="ACME Corp",
            title="Engineer",
            start_date="2020-01",
            end_date="2022-12",
        ),
        ExperienceData(
            id="exp-b",
            organization="ACME Corp",
            title="Engineer",
            start_date="2020-01",
            end_date="2022-12",
        ),
        ExperienceData(
            id="exp-c",
            organization="Other Co",
            title="Engineer",
            start_date="2023-01",
        ),
    ]
    builder = CanonicalProfileBuilder()
    profile = builder.build(person, experiences)

    assert len(profile["experiences"]) == 2


def test_build_experience_ordering_most_recent_first() -> None:
    person = PersonData(id="person-test", first_name="J", last_name="D", full_name="J D")
    experiences = [
        ExperienceData(
            id="exp-old",
            organization="Old Co",
            title="Junior",
            start_date="2018-03",
        ),
        ExperienceData(
            id="exp-mid",
            organization="Mid Co",
            title="Mid",
            start_date="2020-06",
        ),
        ExperienceData(
            id="exp-new",
            organization="New Co",
            title="Senior",
            start_date="2023-01",
        ),
    ]
    builder = CanonicalProfileBuilder()
    profile = builder.build(person, experiences)

    titles = [e["title"] for e in profile["experiences"]]
    assert titles == ["Senior", "Mid", "Junior"]


def test_build_experience_company_normalization() -> None:
    person = PersonData(id="person-test", first_name="J", last_name="D", full_name="J D")
    experiences = [
        ExperienceData(
            id="exp-a",
            organization="IBM",
            title="SWE I",
            start_date="2020-01",
            end_date="2021-12",
        ),
        ExperienceData(
            id="exp-b",
            organization="International Business Machines",
            title="SWE II",
            start_date="2022-01",
            end_date="2023-12",
        ),
    ]
    builder = CanonicalProfileBuilder()
    profile = builder.build(person, experiences)

    assert len(profile["experiences"]) == 2
    assert len(profile["organizations"]) == 1
    assert profile["organizations"][0]["name"] == "IBM"


def test_normalize_company_strips_special_chars() -> None:
    assert normalize_company("ACME, Inc.") == "acme inc"
    assert normalize_company("Data-Robotics Corp!") == "datarobotics corp"


def test_normalize_company_known_abbreviation() -> None:
    assert normalize_company("International Business Machines") == "ibm"


def test_normalize_company_whitespace_collapsed() -> None:
    assert normalize_company("  Very   Wide   ") == "very wide"


def test_normalize_date_present_becomes_empty() -> None:
    assert normalize_date("present") == ""
    assert normalize_date("Present") == ""
    assert normalize_date("PRESENT") == ""


def test_normalize_date_now_and_current() -> None:
    assert normalize_date("now") == ""
    assert normalize_date("current") == ""
    assert normalize_date("ongoing") == ""


def test_normalize_date_passes_through_ym() -> None:
    assert normalize_date("2023-01") == "2023-01"
    assert normalize_date("2020") == "2020"


def test_normalize_date_strips_surrounding_whitespace() -> None:
    assert normalize_date("  2023-01  ") == "2023-01"


def test_build_with_empty_experiences() -> None:
    person = PersonData(id="person-empty", first_name="E", last_name="M", full_name="E M")
    builder = CanonicalProfileBuilder()
    profile = builder.build(person)
    assert profile["experiences"] == []
    assert profile["organizations"] == []


def test_build_with_empty_experiences_list() -> None:
    person = PersonData(id="person-empty", first_name="E", last_name="M", full_name="E M")
    builder = CanonicalProfileBuilder()
    profile = builder.build(person, [])
    assert profile["experiences"] == []
    assert profile["organizations"] == []


def test_normalize_returns_same_structure() -> None:
    person = PersonData(id="p1", first_name="A", last_name="B", full_name="A B")
    exp = ExperienceData(id="e1", organization="Co", title="Dev")
    result = ExtractionResult(person=person, experiences=[exp])
    builder = CanonicalProfileBuilder()
    normalized = builder.normalize(result)
    assert normalized.person.id == "p1"
    assert len(normalized.experiences) == 1
    assert normalized.experiences[0].id == "e1"
    assert normalized.confidence == 0.0
    assert normalized.warnings == []
    assert normalized.source_document is None


def test_normalize_preserves_metadata_fields() -> None:
    person = PersonData(id="p1", first_name="A", last_name="B", full_name="A B")
    exp = ExperienceData(id="e1", organization="Co", title="Dev")
    result = ExtractionResult(
        person=person,
        experiences=[exp],
        confidence=0.85,
        warnings=["low confidence on date"],
        source_document="resume.pdf",
        extraction_timestamp="2025-01-01T00:00:00+00:00",
    )
    builder = CanonicalProfileBuilder()
    normalized = builder.normalize(result)
    assert normalized.confidence == 0.85
    assert normalized.warnings == ["low confidence on date"]
    assert normalized.source_document == "resume.pdf"
    assert normalized.extraction_timestamp == "2025-01-01T00:00:00+00:00"


def test_build_includes_source_traceability() -> None:
    person = PersonData(id="p1", first_name="A", last_name="B", full_name="A B")
    builder = CanonicalProfileBuilder()
    profile = builder.build(
        person,
        source_document="resume.docx",
        extraction_timestamp="2025-06-01T12:00:00+00:00",
    )
    meta = profile["extensions"]["_acquisition"]
    assert meta["sourceDocument"] == "resume.docx"
    assert meta["extractionTimestamp"] == "2025-06-01T12:00:00+00:00"


def test_build_omits_traceability_when_not_provided() -> None:
    person = PersonData(id="p1", first_name="A", last_name="B", full_name="A B")
    builder = CanonicalProfileBuilder()
    profile = builder.build(person)
    assert "_acquisition" not in profile.get("extensions", {})


def test_skill_normalize_canonicalizes_names() -> None:
    builder = SkillBuilder()
    skills = [
        SkillData(name="  C#  "),
        SkillData(name="C Sharp"),
        SkillData(name="csharp"),
        SkillData(name="JS"),
        SkillData(name="JavaScript"),
        SkillData(name="Typescript"),
    ]
    result = builder.normalize(skills)
    names = [s.name for s in result]
    assert "C#" in names
    assert "JavaScript" in names
    assert "TypeScript" in names


def test_skill_normalize_deduplicates() -> None:
    builder = SkillBuilder()
    skills = [
        SkillData(name="Python"),
        SkillData(name="Python"),
        SkillData(name="python"),
    ]
    result = builder.normalize(skills)
    assert len(result) == 1
    assert result[0].name == "Python"


def test_skill_normalize_unknown_name_passes_through() -> None:
    builder = SkillBuilder()
    skills = [SkillData(name="Some Obscure Skill")]
    result = builder.normalize(skills)
    assert result[0].name == "Some Obscure Skill"


def test_skill_normalize_orders_alphabetically() -> None:
    builder = SkillBuilder()
    skills = [
        SkillData(name="Zebra"),
        SkillData(name="Alpha"),
        SkillData(name="Bravo"),
    ]
    result = builder.normalize(skills)
    assert [s.name for s in result] == ["Alpha", "Bravo", "Zebra"]


def test_skill_build_creates_skill_dict() -> None:
    from careeros.acquisition.builders import BuilderContext

    builder = SkillBuilder()
    skills = [
        SkillData(name="Python", category="Language", proficiency="Advanced"),
    ]
    result = builder.build_many(skills, BuilderContext())
    assert len(result) == 1
    entry = result[0]
    assert entry["id"] == "skill-python"
    assert entry["name"] == "Python"
    assert entry["category"] == "Language"
    assert entry["extensions"]["proficiency"] == "Advanced"


def test_skill_associate_evidence_links_to_experiences() -> None:
    builder = SkillBuilder()
    skills = [SkillData(name="Kubernetes")]
    exps = [
        ExperienceData(
            id="exp-1",
            organization="Co",
            title="Dev",
            technologies=["Docker", "Kubernetes"],
        ),
    ]
    result = builder.associate_evidence(skills, exps)
    assert len(result[0].evidence) == 1
    assert result[0].evidence[0]["experienceId"] == "exp-1"


def test_skill_associate_evidence_no_match() -> None:
    builder = SkillBuilder()
    skills = [SkillData(name="Python")]
    exps = [
        ExperienceData(
            id="exp-1",
            organization="Co",
            title="Dev",
            technologies=["Java"],
        ),
    ]
    result = builder.associate_evidence(skills, exps)
    assert result[0].evidence == []


def test_skill_associate_evidence_matches_after_normalization() -> None:
    builder = SkillBuilder()
    skills = builder.normalize([SkillData(name="JS")])
    exps = [
        ExperienceData(
            id="exp-1",
            organization="Co",
            title="Dev",
            technologies=["JavaScript"],
        ),
    ]
    result = builder.associate_evidence(skills, exps)
    assert len(result[0].evidence) == 1
    assert result[0].evidence[0]["experienceId"] == "exp-1"


def test_build_with_skills_includes_skill_entries() -> None:
    person = PersonData(id="p1", first_name="A", last_name="B", full_name="A B")
    builder = CanonicalProfileBuilder()
    skills = [SkillData(name="Python")]
    profile = builder.build(person, skills=skills)
    assert len(profile["skills"]) == 1
    assert profile["skills"][0]["name"] == "Python"


def test_build_with_skills_deduplicates_and_evidences() -> None:
    person = PersonData(id="p1", first_name="A", last_name="B", full_name="A B")
    experiences = [
        ExperienceData(
            id="exp-1",
            organization="Co",
            title="Dev",
            technologies=["Python"],
        ),
    ]
    skills = [
        SkillData(name="Python"),
        SkillData(name="python"),
    ]
    builder = CanonicalProfileBuilder()
    profile = builder.build(person, experiences, skills)
    assert len(profile["skills"]) == 1
    assert profile["skills"][0]["name"] == "Python"
    ext = profile["skills"][0].get("extensions", {})
    assert len(ext.get("experienceEvidence", [])) == 1


# ── EducationBuilder tests ────────────────────────────────────────────────────


def test_education_normalize_canonicalizes_institution() -> None:
    builder = EducationBuilder()
    items = [EducationData(institution="  MIT  ", degree="B.S.")]
    result = builder.normalize(items)
    assert result[0].institution == "Massachusetts Institute of Technology"


def test_education_normalize_unknown_institution_passes_through() -> None:
    builder = EducationBuilder()
    items = [EducationData(institution="Some Unknown University", degree="B.A.")]
    result = builder.normalize(items)
    assert result[0].institution == "Some Unknown University"


def test_education_normalize_deduplicates() -> None:
    builder = EducationBuilder()
    items = [
        EducationData(institution="MIT", degree="B.S.", start_date="2014", end_date="2018"),
        EducationData(institution="Massachusetts Institute of Technology", degree="B.S.", start_date="2014", end_date="2018"),
    ]
    result = builder.normalize(items)
    assert len(result) == 1
    assert result[0].institution == "Massachusetts Institute of Technology"


def test_education_normalize_detects_current() -> None:
    builder = EducationBuilder()
    items = [EducationData(institution="KTH", degree="M.Sc.", end_date="present")]
    result = builder.normalize(items)
    assert result[0].is_current is True
    assert result[0].end_date is None


def test_education_normalize_explicit_not_current() -> None:
    builder = EducationBuilder()
    items = [EducationData(institution="KTH", degree="M.Sc.", end_date="2020-06", is_current=False)]
    result = builder.normalize(items)
    assert result[0].is_current is False
    assert result[0].end_date == "2020-06"


def test_education_normalize_orders_most_recent_first() -> None:
    builder = EducationBuilder()
    items = [
        EducationData(institution="A", degree="a", start_date="2018"),
        EducationData(institution="B", degree="b", start_date="2020"),
        EducationData(institution="C", degree="c", start_date="2016"),
    ]
    result = builder.normalize(items)
    institutions = [e.institution for e in result]
    assert institutions == ["B", "A", "C"]


def test_education_normalize_missing_dates_passes_through() -> None:
    builder = EducationBuilder()
    items = [EducationData(institution="MIT", degree="B.S.")]
    result = builder.normalize(items)
    assert len(result) == 1
    assert result[0].start_date is None
    assert result[0].end_date is None


def test_education_build_creates_education_dict() -> None:
    from careeros.acquisition.builders import BuilderContext

    builder = EducationBuilder()
    items = [EducationData(institution="KTH Royal Institute of Technology", degree="M.Sc.")]
    result = builder.build_many(items, BuilderContext())
    assert len(result) == 1
    entry = result[0]
    assert "edu-" in entry["id"]
    assert entry["program"] == "M.Sc."
    assert entry["institutionRef"]["id"] == "org-kth-royal-institute-of-technology"


def test_education_build_with_full_fields() -> None:
    from careeros.acquisition.builders import BuilderContext

    builder = EducationBuilder()
    items = [EducationData(
        institution="MIT",
        degree="B.S.",
        field_of_study="CS",
        start_date="2014-09",
        end_date="2018-06",
        is_current=False,
    )]
    result = builder.build_many(items, BuilderContext())
    entry = result[0]
    assert entry["fieldOfStudy"] == "CS"
    assert entry["dateRange"]["start"] == "2014-09"
    assert entry["dateRange"]["end"] == "2018-06"
    assert entry["dateRange"]["isCurrent"] is False


def test_education_in_built_profile() -> None:
    person = PersonData(id="p1", first_name="A", last_name="B", full_name="A B")
    education = [EducationData(institution="MIT", degree="B.S.")]
    builder = CanonicalProfileBuilder()
    profile = builder.build(person, education=education)
    assert len(profile["education"]) == 1
    assert profile["education"][0]["program"] == "B.S."
    # MIT alias resolved
    assert profile["education"][0]["institutionRef"]["id"] == "org-massachusetts-institute-of-technology"


def test_education_in_normalize_result() -> None:
    person = PersonData(id="p1", first_name="A", last_name="B", full_name="A B")
    edu = EducationData(institution="MIT", degree="B.S.")
    result = ExtractionResult(person=person, education=[edu])
    builder = CanonicalProfileBuilder()
    normalized = builder.normalize(result)
    assert len(normalized.education) == 1
    assert normalized.education[0].institution == "Massachusetts Institute of Technology"


# ── BuilderRegistry tests ──────────────────────────────────────────────────────


class _FakeBuilder(SkillBuilder):
    pass


def test_registry_register_and_get() -> None:
    registry = BuilderRegistry()
    builder = SkillBuilder()
    registry.register(SkillData, builder)
    assert registry.get(SkillData) is builder


def test_registry_get_returns_none_for_unknown_type() -> None:
    registry = BuilderRegistry()
    assert registry.get(PersonData) is None


def test_registry_rejects_duplicate_registration() -> None:
    registry = BuilderRegistry()
    registry.register(SkillData, SkillBuilder())
    import pytest

    with pytest.raises(ValueError, match="already registered"):
        registry.register(SkillData, SkillBuilder())


def test_registry_rejects_non_builder() -> None:
    registry = BuilderRegistry()
    import pytest

    with pytest.raises(TypeError, match="Expected BaseBuilder"):
        registry.register(SkillData, "not a builder")  # type: ignore[arg-type]


def test_registry_ordering_is_deterministic() -> None:
    registry = BuilderRegistry()
    registry.register(PersonData, SkillBuilder())
    registry.register(ExperienceData, SkillBuilder())
    registry.register(SkillData, SkillBuilder())

    types = [t for t, _ in registry.all()]
    assert types == [PersonData, ExperienceData, SkillData]
    assert registry.all() == registry.all()


def test_builder_lifecycle_normalize_prepare_build() -> None:
    from careeros.acquisition.builders import BuilderContext

    builder = SkillBuilder()
    raw = [SkillData(name="  Python  "), SkillData(name="JS")]

    normalized = builder.normalize(raw)
    names = [s.name for s in normalized]
    assert "Python" in names
    assert "JavaScript" in names

    prepared = builder.prepare(normalized, {})
    assert prepared is not normalized
    assert len(prepared) == 2

    built = builder.build_many(prepared, BuilderContext())
    assert len(built) == 2


def test_no_builder_calls_another_builder_directly() -> None:
    import inspect

    from careeros.acquisition.builders import (
        ExperienceBuilder,
        PersonBuilder,
        SkillBuilder,
    )

    referenced = ["BaseBuilder", "BuilderContext", "BuilderRegistry",
                   "SkillData", "ExperienceData", "PersonData",
                   "normalize_company", "normalize_date",
                   "extract_year", "extract_month",
                   "SKILL_ALIASES"]

    for b in [PersonBuilder(), ExperienceBuilder(), SkillBuilder()]:
        source = inspect.getsource(type(b))
        for other in ["PersonBuilder", "ExperienceBuilder", "SkillBuilder"]:
            if other == type(b).__name__:
                continue
            assert other not in source, f"{type(b).__name__} references {other}"
