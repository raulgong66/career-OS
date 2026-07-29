import pytest

from careeros.acquisition.llm_extractor import LLMExtractionError, LLMExtractor


class _ConcreteExtractor(LLMExtractor):
    def extract(self, text, schema=None):
        raise NotImplementedError


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