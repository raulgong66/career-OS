from pathlib import Path

import pytest

from careeros.exceptions import EntityNotFoundError, ValidationError
from careeros.export_contract import ExportContractBuilder
from careeros.schema_loader import SchemaLoader


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def builder(repo_root):
    return ExportContractBuilder(SchemaLoader(repo_root / "schemas"))


@pytest.fixture
def profile():
    return {
        "profileVersion": "1.0.0",
        "person": {
            "id": "person-1",
            "names": [{"value": "Jane Doe", "usage": "professional"}],
            "positioning": {
                "headline": "AI product builder",
                "valueProposition": "Builds reliable AI workflows",
                "targetDirection": "AI platform roles",
                "themes": ["AI", "Product"],
            },
        },
        "skills": [
            {
                "id": "skill-1",
                "name": "AI workflow design",
            }
        ],
        "projects": [
            {
                "id": "project-1",
                "name": "CareerOS",
            }
        ],
        "targetContexts": [
            {
                "id": "context-1",
                "label": "AI platform role",
                "audience": "Hiring manager",
                "role": "AI Product Engineer",
                "market": "AI platforms",
                "language": "en",
                "emphasis": ["AI", "workflow design"],
            }
        ],
        "artifacts": [
            {
                "id": "artifact-1",
                "title": "AI platform CV",
                "artifactType": "CV",
                "targetContextRefs": [{"id": "context-1", "type": "targetContext"}],
                "sourceRefs": [
                    {"id": "skill-1", "type": "skill"},
                    {"id": "project-1", "type": "project"},
                ],
                "derivedFromProfileVersion": "1.0.0",
            }
        ],
    }


def test_export_contract_resolves_artifact_context_and_sources(builder, profile):
    contract = builder.build(profile, "artifact-1")

    assert contract.profile_version == "1.0.0"
    assert contract.artifact_type == "CV"
    assert contract.target_contexts[0]["id"] == "context-1"
    assert [source.id for source in contract.sources] == ["skill-1", "project-1"]
    assert contract.sources[0].data["name"] == "AI workflow design"


def test_export_contract_serializes_to_provider_agnostic_shape(builder, profile):
    payload = builder.build(profile, "artifact-1").to_dict()

    assert payload["artifactId"] == "artifact-1"
    assert payload["artifactType"] == "CV"
    assert payload["person"]["id"] == "person-1"
    assert payload["targetContexts"][0]["role"] == "AI Product Engineer"
    assert payload["sources"][0]["type"] == "skill"
    assert "provider" not in payload


def test_export_contract_rejects_missing_artifact(builder, profile):
    with pytest.raises(EntityNotFoundError, match="Artifact not found"):
        builder.build(profile, "missing")


def test_export_contract_rejects_missing_target_context(builder, profile):
    profile["artifacts"][0]["targetContextRefs"] = [{"id": "missing", "type": "targetContext"}]

    with pytest.raises(EntityNotFoundError, match="Target context not found"):
        builder.build(profile, "artifact-1")


def test_export_contract_rejects_missing_source(builder, profile):
    profile["artifacts"][0]["sourceRefs"] = [{"id": "missing", "type": "skill"}]

    with pytest.raises(EntityNotFoundError, match="Source not found"):
        builder.build(profile, "artifact-1")


def test_export_contract_validates_profile_with_existing_schema(builder, profile):
    profile.pop("profileVersion")

    with pytest.raises(ValidationError) as exc_info:
        builder.build(profile, "artifact-1")

    assert exc_info.value.errors
