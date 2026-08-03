"""Unit tests for the CSKS data model (M1.22)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from careeros.csks.models import (
    CSKSAnswer,
    Citation,
    ExtractedEntity,
    ExtractedRelationship,
    StructuredQueryResult,
    is_valid_entity_type,
    is_valid_relationship_type,
    make_entity_id,
    make_relationship_id,
)


def test_extracted_entity_is_frozen() -> None:
    entity = ExtractedEntity(
        entity_type="component",
        id="component.widgets.Widget",
        properties={"name": "Widget"},
        source_path="careeros/widgets.py",
        line_start=1,
        line_end=3,
    )
    with pytest.raises(FrozenInstanceError):
        entity.properties = {}  # type: ignore[misc]


def test_extracted_entity_defaults_confidence_to_one() -> None:
    entity = ExtractedEntity(
        entity_type="rule",
        id="rule.total_years_experience",
        properties={},
        source_path="careeros/rules.py",
        line_start=1,
        line_end=1,
    )
    assert entity.confidence == 1.0


def test_extracted_relationship_is_frozen_and_has_default_properties() -> None:
    rel = ExtractedRelationship(
        from_id="a",
        to_id="b",
        relationship_type="depends_on",
    )
    assert rel.properties == {}
    assert rel.confidence == 1.0
    with pytest.raises(FrozenInstanceError):
        rel.from_id = "c"  # type: ignore[misc]


def test_citation_fields() -> None:
    citation = Citation(
        file="docs/adr/0001-storage.md",
        line_start=1,
        line_end=3,
        text="ADR 0001",
        entity_id="adr.001",
    )
    assert citation.file.endswith("0001-storage.md")
    assert citation.entity_id == "adr.001"


def test_structured_query_result_is_frozen() -> None:
    result = StructuredQueryResult(
        answer="answer",
        citations=(),
        matched_entities=(),
        traversal_path=(),
        confidence=1.0,
        entities_found=0,
        query_time_ms=1,
        query_type="entity_lookup",
    )
    assert result.query_type == "entity_lookup"
    with pytest.raises(FrozenInstanceError):
        result.answer = "other"  # type: ignore[misc]


def test_csks_answer_is_frozen() -> None:
    answer = CSKSAnswer(
        answer="answer",
        citations=(),
        confidence=1.0,
        entities_found=1,
        query_time_ms=2,
        query_type="type_filter",
    )
    assert answer.entities_found == 1
    with pytest.raises(FrozenInstanceError):
        answer.answer = "other"  # type: ignore[misc]


def test_make_entity_id_is_deterministic() -> None:
    assert make_entity_id("component", "Profile Loader") == "component.profile_loader"
    assert make_entity_id("component", "Profile Loader") == make_entity_id("component", "Profile Loader")


def test_make_relationship_id_is_deterministic() -> None:
    rel_id = make_relationship_id("domain.profile", "domain.schema", "depends_on")
    assert rel_id == "domain.profile--depends_on--domain.schema"


def test_valid_entity_type() -> None:
    assert is_valid_entity_type("domain")
    assert is_valid_entity_type("component")
    assert is_valid_entity_type("api_endpoint")
    assert is_valid_entity_type("rule")
    assert not is_valid_entity_type("bogus")


def test_valid_relationship_type() -> None:
    assert is_valid_relationship_type("depends_on")
    assert is_valid_relationship_type("contains")
    assert not is_valid_relationship_type("bogus")


def test_query_type_is_a_literal_alias() -> None:
    from careeros.csks.models import QueryType

    assert "entity_lookup" in QueryType.__args__  # type: ignore[attr-defined]
    assert "unknown" in QueryType.__args__  # type: ignore[attr-defined]


def test_all_csks_models_are_frozen_dataclasses() -> None:
    for cls in (ExtractedEntity, ExtractedRelationship, Citation, StructuredQueryResult, CSKSAnswer):
        assert cls.__dataclass_params__.frozen is True
        assert cls.__dataclass_params__.eq is True
