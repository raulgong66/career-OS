import json

import pytest

from careeros.acquisition.llm_extractor import (
    LLMExtractionError,
    LLMExtractor,
    TruncatedResponseError,
)
from careeros.ai import MockAIProvider


class _ConcreteExtractor(LLMExtractor):
    def extract(self, text, schema=None):
        raise NotImplementedError


class _RecordingProvider(MockAIProvider):
    def __init__(self) -> None:
        super().__init__(
            responses={
                "extractor": json.dumps(
                    {"person": {}, "experiences": [], "skills": [], "education": []}
                )
            }
        )
        self.captured: list[tuple[str, int | None, bool]] = []

    def generate(self, prompt, *, temperature=0.1, timeout=60.0, max_tokens=None, json_mode=False):
        self.captured.append((prompt, max_tokens, json_mode))
        return super().generate(prompt, temperature=temperature, timeout=timeout)


def test_build_prompt_contains_person_section() -> None:
    extractor = _ConcreteExtractor()
    prompt = extractor.build_prompt("dummy text")
    assert "person" in prompt.lower()
    assert "firstName" in prompt
    assert "lastName" in prompt
    assert "fullName" in prompt


def test_build_prompt_contains_experiences_section() -> None:
    extractor = _ConcreteExtractor()
    prompt = extractor.build_prompt("dummy text")
    assert "experiences" in prompt.lower()
    assert "organization" in prompt
    assert "title" in prompt
    assert "startDate" in prompt
    assert "endDate" in prompt
    assert "isCurrent" in prompt


def test_build_prompt_contains_skills_section() -> None:
    extractor = _ConcreteExtractor()
    prompt = extractor.build_prompt("dummy text")
    assert "skills" in prompt.lower()
    assert "proficiency" in prompt
    assert "category" in prompt


def test_build_prompt_contains_document_text() -> None:
    extractor = _ConcreteExtractor()
    text = "Resume content here"
    prompt = extractor.build_prompt(text)
    assert text in prompt


def test_build_prompt_instructs_json_only() -> None:
    extractor = _ConcreteExtractor()
    prompt = extractor.build_prompt("dummy")
    assert "JSON only" in prompt or "ONLY a JSON" in prompt


def test_parse_response_plain_json() -> None:
    extractor = _ConcreteExtractor()
    raw = '{"person": {"id": "p1"}, "experiences": []}'
    data = extractor.parse_response(raw)
    assert data["person"]["id"] == "p1"


def test_parse_response_with_markdown_code_fences() -> None:
    extractor = _ConcreteExtractor()
    raw = '```json\n{"person": {"id": "p1"}, "experiences": []}\n```'
    data = extractor.parse_response(raw)
    assert data["person"]["id"] == "p1"


def test_parse_response_with_triple_backtick_no_lang() -> None:
    extractor = _ConcreteExtractor()
    raw = '```\n{"person": {"id": "p1"}, "experiences": []}\n```'
    data = extractor.parse_response(raw)
    assert data["person"]["id"] == "p1"


def test_parse_response_with_surrounding_whitespace() -> None:
    extractor = _ConcreteExtractor()
    raw = '  \n  \n{"person": {"id": "p1"}}  \n  '
    data = extractor.parse_response(raw)
    assert data["person"]["id"] == "p1"


def test_parse_response_non_dict_raises_error() -> None:
    extractor = _ConcreteExtractor()
    with pytest.raises(LLMExtractionError, match="not a JSON object"):
        extractor.parse_response('["list", "not", "dict"]')


def test_parse_response_invalid_json_raises_error() -> None:
    extractor = _ConcreteExtractor()
    with pytest.raises(LLMExtractionError, match="Failed to parse"):
        extractor.parse_response("{invalid json}")


def test_to_experience_data_empty() -> None:
    extractor = _ConcreteExtractor()
    result = extractor.to_experience_data({"experiences": []})
    assert result == []


def test_to_experience_data_missing_key() -> None:
    extractor = _ConcreteExtractor()
    result = extractor.to_experience_data({})
    assert result == []


def test_to_experience_data_non_list() -> None:
    extractor = _ConcreteExtractor()
    result = extractor.to_experience_data({"experiences": "not a list"})
    assert result == []


def test_to_experience_data_skips_non_dict_entries() -> None:
    extractor = _ConcreteExtractor()
    data = {"experiences": [{"id": "e1", "organization": "Co", "title": "Dev"}, "not a dict"]}
    result = extractor.to_experience_data(data)
    assert len(result) == 1
    assert result[0].id == "e1"


def test_to_experience_data_partial_fields() -> None:
    extractor = _ConcreteExtractor()
    data = {
        "experiences": [
            {"id": "e1", "organization": "Co", "title": "Dev"},
            {"id": "e2", "title": "Lead", "startDate": "2023-01"},
        ]
    }
    result = extractor.to_experience_data(data)
    assert len(result) == 2
    assert result[0].organization == "Co"
    assert result[0].title == "Dev"
    assert result[1].organization == ""
    assert result[1].title == "Lead"
    assert result[1].start_date == "2023-01"


def test_to_person_data_with_wrapper_key() -> None:
    extractor = _ConcreteExtractor()
    data = {"person": {"id": "p1", "firstName": "A", "lastName": "B", "fullName": "A B"}}
    person = extractor.to_person_data(data)
    assert person.id == "p1"
    assert person.first_name == "A"


def test_to_person_data_without_wrapper_key() -> None:
    extractor = _ConcreteExtractor()
    data = {"id": "p1", "firstName": "A", "lastName": "B", "fullName": "A B"}
    person = extractor.to_person_data(data)
    assert person.id == "p1"
    assert person.first_name == "A"


def test_to_person_data_fallback_id() -> None:
    extractor = _ConcreteExtractor()
    person = extractor.to_person_data({})
    assert person.id == "person-unknown"


def test_to_person_data_null_id_falls_back() -> None:
    extractor = _ConcreteExtractor()
    person = extractor.to_person_data(
        {"person": {"id": None, "firstName": "Anna", "lastName": "Lindqvist"}}
    )
    assert person.id == "person-unknown"
    assert person.first_name == "Anna"


def test_to_person_data_empty_id_falls_back() -> None:
    extractor = _ConcreteExtractor()
    person = extractor.to_person_data(
        {"person": {"id": "", "fullName": "Anna Lindqvist"}}
    )
    assert person.id == "person-unknown"


def test_to_person_data_non_dict_person_falls_back() -> None:
    extractor = _ConcreteExtractor()
    person = extractor.to_person_data({"person": "Anna Lindqvist"})
    assert person.id == "person-unknown"
    assert person.full_name == ""


def test_to_person_data_null_person_falls_back() -> None:
    extractor = _ConcreteExtractor()
    person = extractor.to_person_data({"person": None})
    assert person.id == "person-unknown"


def test_to_experience_data_null_id_falls_back() -> None:
    extractor = _ConcreteExtractor()
    result = extractor.to_experience_data(
        {"experiences": [{"id": None, "organization": "Co", "title": "Dev"}]}
    )
    assert len(result) == 1
    assert result[0].id == "exp-0"


def test_to_result_combines_person_and_experiences() -> None:
    extractor = _ConcreteExtractor()
    data = {
        "person": {"id": "p1", "firstName": "X", "lastName": "Y", "fullName": "X Y"},
        "experiences": [{"id": "e1", "organization": "Co", "title": "Dev"}],
        "skills": [{"name": "Python", "category": "Language"}],
    }
    result = extractor.to_result(data)
    assert result.person.id == "p1"
    assert len(result.experiences) == 1
    assert result.experiences[0].organization == "Co"
    assert len(result.skills) == 1
    assert result.skills[0].name == "Python"


def test_extract_requests_json_mode_and_max_tokens() -> None:
    provider = _RecordingProvider()
    extractor = LLMExtractor(provider=provider)

    extractor.extract("some resume text")

    assert len(provider.captured) == 1
    prompt, max_tokens, json_mode = provider.captured[0]
    assert json_mode is True
    assert max_tokens == LLMExtractor.extraction_max_tokens
    assert "some resume text" in prompt


def test_extract_chunks_large_documents() -> None:
    provider = _RecordingProvider()
    extractor = LLMExtractor(provider=provider)
    extractor.chunk_size = 200

    extractor.extract(" ".join(f"sentence number {i}." for i in range(400)))

    assert len(provider.captured) > 1
    for prompt, _, _ in provider.captured:
        assert "sentence number" in prompt


def test_extract_single_chunk_for_small_document() -> None:
    provider = _RecordingProvider()
    extractor = LLMExtractor(provider=provider)

    extractor.extract("short resume text")

    assert len(provider.captured) == 1


def test_extract_adds_chunk_warning_for_large_document() -> None:
    provider = _RecordingProvider()
    extractor = LLMExtractor(provider=provider)
    extractor.chunk_size = 100

    result = extractor.extract("word " * 500)

    assert any("split into" in w for w in result.warnings)


class _TruncatingProvider(MockAIProvider):
    def __init__(self, threshold: int = 2000) -> None:
        super().__init__(
            responses={
                "extractor": json.dumps(
                    {
                        "person": {"id": "person-x", "fullName": "X Sample"},
                        "experiences": [
                            {
                                "id": "exp-1",
                                "organization": "ACME",
                                "title": "Engineer",
                                "startDate": "2020-01",
                                "isCurrent": True,
                            }
                        ],
                        "skills": [],
                        "education": [],
                    }
                )
            }
        )
        self.threshold = threshold

    def _embedded_text(self, prompt: str) -> str:
        marker = "Document text:\n---\n"
        if marker not in prompt:
            return prompt
        body = prompt.split(marker, 1)[1]
        return body.rsplit("\n---\n", 1)[0]

    def generate(self, prompt, *, temperature=0.1, timeout=60.0, max_tokens=None, json_mode=False):
        if len(self._embedded_text(prompt)) > self.threshold:
            return (
                '{"person": {"id": "person-x", "fullName": "X Sample"}, '
                '"experiences": [{"id": "exp-1", "organization": "ACME", '
                '"title": "Engineer", "startDate": "2020-01"'
            )
        return super().generate(prompt, temperature=temperature, timeout=timeout)


def test_extract_splits_truncated_chunk_and_recovers() -> None:
    provider = _TruncatingProvider(threshold=2000)
    extractor = LLMExtractor(provider=provider)

    result = extractor.extract("BEGIN " * 3000)

    assert result.person.full_name == "X Sample"
    assert any(e.organization == "ACME" for e in result.experiences)
    assert any("split for retry" in w for w in result.warnings)


def test_merge_results_first_non_empty_person_wins() -> None:
    from careeros.acquisition.person_data import ExtractionResult, PersonData

    extractor = _ConcreteExtractor()
    result = extractor.merge_results(
        [
            ExtractionResult(person=PersonData(id="person-unknown", first_name="", last_name="", full_name="")),
            ExtractionResult(
                person=PersonData(
                    id="person-real",
                    first_name="Alex",
                    last_name="Johnson",
                    full_name="Alex Johnson",
                    email="a@b.c",
                )
            ),
        ]
    )
    assert result.person.id == "person-real"
    assert result.person.first_name == "Alex"
    assert result.person.email == "a@b.c"


def test_merge_results_concatenates_entities() -> None:
    from careeros.acquisition.person_data import EducationData, ExperienceData, ExtractionResult, PersonData, SkillData

    extractor = _ConcreteExtractor()
    result = extractor.merge_results(
        [
            ExtractionResult(
                person=PersonData(id="p1", first_name="A", last_name="B", full_name="A B"),
                experiences=[ExperienceData(id="e1", organization="Co", title="Dev")],
                skills=[SkillData(name="Python")],
            ),
            ExtractionResult(
                person=PersonData(id="person-unknown", first_name="", last_name="", full_name=""),
                experiences=[ExperienceData(id="e2", organization="Acme", title="Lead")],
                skills=[SkillData(name="Kubernetes")],
                education=[EducationData(institution="KTH", degree="M.S.")],
            ),
        ]
    )
    assert [e.organization for e in result.experiences] == ["Co", "Acme"]
    assert [s.name for s in result.skills] == ["Python", "Kubernetes"]
    assert len(result.education) == 1
    assert result.person.full_name == "A B"


def test_merge_results_empty_list() -> None:
    extractor = _ConcreteExtractor()
    result = extractor.merge_results([])
    assert result.person.id == "person-unknown"


def test_normalize_response_maps_alternate_schema() -> None:
    extractor = _ConcreteExtractor()
    data = {
        "PersonalDetails": {
            "FullName": "Alex Johnson",
            "Email": "alex@example.com",
            "DateOfBirth": "1978-02-28",
            "Nationality": "Swedish",
        },
        "WorkExperience": [
            {
                "Company": "Lexher",
                "Role": "Sr Network Engineer",
                "Duration": "Sep 2022 - Present",
                "Responsibilities": ["Architect routing topologies"],
                "Technologies": ["Cisco", "BGP"],
            },
            {
                "Company": "Telia",
                "Role": "Network Engineer",
                "Duration": "Feb 2015 - Feb 2019",
            },
        ],
        "Skills": [{"Skill": "BGP", "Category": "Technology"}],
        "Education": [{"University": "KTH", "Degree": "M.S."}],
    }

    normalized = extractor.normalize_response(data)

    assert normalized["person"]["fullName"] == "Alex Johnson"
    assert normalized["person"]["email"] == "alex@example.com"
    exp = normalized["experiences"]
    assert exp[0]["organization"] == "Lexher"
    assert exp[0]["title"] == "Sr Network Engineer"
    assert exp[0]["startDate"] == "2022-09"
    assert exp[0]["isCurrent"] is True
    assert exp[0]["responsibilities"] == ["Architect routing topologies"]
    assert exp[0]["technologies"] == ["Cisco", "BGP"]
    assert exp[1]["startDate"] == "2015-02"
    assert exp[1]["endDate"] == "2019-02"
    assert exp[1]["isCurrent"] is False
    assert normalized["skills"][0] == {"name": "BGP", "category": "Technology"}
    assert normalized["education"][0] == {"institution": "KTH", "degree": "M.S."}


def test_normalize_response_keeps_canonical_keys_and_prefers_them() -> None:
    extractor = _ConcreteExtractor()
    data = {
        "person": {"id": "p1", "fullName": "Canonical"},
        "PersonalDetails": {"FullName": "Alternate"},
        "experiences": [{"id": "e1", "organization": "Co", "title": "Dev"}],
        "WorkExperience": [{"Company": "Other"}],
    }

    normalized = extractor.normalize_response(data)

    assert normalized["person"]["fullName"] == "Canonical"
    assert normalized["experiences"] == [{"id": "e1", "organization": "Co", "title": "Dev"}]


def test_split_duration_variants() -> None:
    extractor = _ConcreteExtractor()
    assert extractor._split_duration("Sep 2022 - Present") == ("2022-09", None, True)
    assert extractor._split_duration("Feb 2015 - Feb 2019") == ("2015-02", "2019-02", False)
    assert extractor._split_duration("2019 - 2021") == ("2019", "2021", False)
    assert extractor._split_duration("2020 - Present") == ("2020", None, True)
    assert extractor._split_duration("") == (None, None, False)


def test_to_result_accepts_alternate_schema() -> None:
    extractor = _ConcreteExtractor()
    data = {
        "PersonalDetails": {"FullName": "Alex Johnson", "Email": "alex@example.com"},
        "WorkExperience": [
            {
                "Company": "Lexher",
                "Role": "Sr Network Engineer",
                "Duration": "Sep 2022 - Present",
            }
        ],
        "Skills": [{"Skill": "BGP"}],
        "Education": [{"University": "KTH", "Degree": "M.S."}],
    }

    result = extractor.to_result(data)

    assert result.person.full_name == "Alex Johnson"
    assert result.person.email == "alex@example.com"
    assert result.experiences[0].organization == "Lexher"
    assert result.experiences[0].title == "Sr Network Engineer"
    assert result.experiences[0].start_date == "2022-09"
    assert result.experiences[0].is_current is True
    assert result.skills[0].name == "BGP"
    assert result.education[0].institution == "KTH"
    assert result.education[0].degree == "M.S."


def test_parse_response_with_markdown_json_fences_and_explanatory_text() -> None:
    extractor = _ConcreteExtractor()
    raw = (
        "Here is the extracted profile:\n"
        "```json\n"
        '{"person": {"id": "p1"}, "experiences": []}\n'
        "```\n"
        "Hope this helps!"
    )
    data = extractor.parse_response(raw)
    assert data["person"]["id"] == "p1"


def test_parse_response_ignores_explanatory_text() -> None:
    extractor = _ConcreteExtractor()
    raw = (
        'Sure! Based on the document, here is the result: '
        '{"person": {"id": "p1"}, "experiences": []} '
        "If you need anything else, just ask."
    )
    data = extractor.parse_response(raw)
    assert data["person"]["id"] == "p1"


def test_parse_response_recovery_trailing_comma() -> None:
    extractor = _ConcreteExtractor()
    raw = '{"person": {"id": "p1",}, "experiences": [],}'
    data = extractor.parse_response(raw)
    assert data["person"]["id"] == "p1"


def test_parse_response_truncated_raises_truncated_error() -> None:
    extractor = _ConcreteExtractor()
    raw = (
        '{"person": {"id": "p1"}, "experiences": [{"id": "e1", '
        '"organization": "Lexher", "role": "Sr Network Engineer",'
    )
    with pytest.raises(TruncatedResponseError, match="truncated mid-JSON"):
        extractor.parse_response(raw)


def test_parse_response_malformed_raises_parse_error() -> None:
    extractor = _ConcreteExtractor()
    with pytest.raises(LLMExtractionError, match="Failed to parse"):
        extractor.parse_response('{"person": {"id": "p1", "broken": }}')


def test_parse_response_no_json_object_raises() -> None:
    extractor = _ConcreteExtractor()
    with pytest.raises(LLMExtractionError, match="no JSON object found"):
        extractor.parse_response("The model did not return any JSON at all.")