from careeros.evidence_selector import EvidenceSelector
from careeros.export_contract import ExportContract, ExportSource


def _contract() -> ExportContract:
    return ExportContract(
        profile_version="1.0.0",
        artifact_id="artifact-1",
        artifact_type="CV",
        person={"id": "person-1"},
        artifact={"id": "artifact-1"},
        target_contexts=[{"id": "context-1"}],
        sources=[
            ExportSource(
                type="skill",
                id="skill-general",
                data={"id": "skill-general", "name": "General skill"},
                ref={"id": "skill-general", "type": "skill"},
            ),
            ExportSource(
                type="skill",
                id="skill-match",
                data={
                    "id": "skill-match",
                    "name": "Matching skill",
                    "targetContextRefs": [{"id": "context-1", "type": "targetContext"}],
                },
                ref={"id": "skill-match", "type": "skill"},
            ),
            ExportSource(
                type="skill",
                id="skill-other",
                data={
                    "id": "skill-other",
                    "name": "Other skill",
                    "targetContextRefs": [{"id": "context-2", "type": "targetContext"}],
                },
                ref={"id": "skill-other", "type": "skill"},
            ),
        ],
    )


def test_evidence_selector_filters_sources_by_target_context() -> None:
    selected = EvidenceSelector().select(_contract())

    assert [source.id for source in selected.sources] == ["skill-general", "skill-match"]


def test_evidence_selector_preserves_source_order() -> None:
    selected = EvidenceSelector().select(_contract())

    assert selected.sources[0].id == "skill-general"
    assert selected.sources[1].id == "skill-match"


def test_evidence_selector_uses_ref_level_target_contexts() -> None:
    contract = _contract()
    contract.sources[0].ref["targetContextRefs"] = [{"id": "context-2", "type": "targetContext"}]

    selected = EvidenceSelector().select(contract)

    assert [source.id for source in selected.sources] == ["skill-match"]


def test_evidence_selector_does_not_mutate_original_contract() -> None:
    contract = _contract()

    selected = EvidenceSelector().select(contract)

    assert len(contract.sources) == 3
    assert len(selected.sources) == 2


def test_evidence_selector_drops_constrained_sources_without_artifact_context() -> None:
    contract = _contract()
    contract.target_contexts = []

    selected = EvidenceSelector().select(contract)

    assert [source.id for source in selected.sources] == ["skill-general"]
