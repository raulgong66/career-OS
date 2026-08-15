import copy

from datetime import datetime, timezone
from typing import Any

import pytest

from careeros.knowledge import KnowledgeGraph, KnowledgeGraphBuilder
from careeros.reasoning import (
    AnalysisModel,
    CircularDependencyError,
    DuplicateRuleError,
    Evidence,
    EvidencePackage,
    EvidencePackageAssembler,
    EvidenceSet,
    MissingDependencyError,
    ReasoningEngine,
    ReasoningReport,
    ReasoningResult,
    Rule,
    RuleContext,
    RuleRegistry,
)

# ---------------------------------------------------------------------------
# Helper: concrete rules for testing
# ---------------------------------------------------------------------------


class DummyRuleA(Rule):
    id = "rule_a"
    name = "Rule A"
    description = "First test rule"

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        return [
            ReasoningResult(
                rule_id=self.id,
                finding_type="experience_count",
                value=len(context.graph.experiences()),
                confidence=1.0,
            )
        ]


class DummyRuleB(Rule):
    id = "rule_b"
    name = "Rule B"
    description = "Second test rule"
    dependencies = ["rule_a"]

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        return [
            ReasoningResult(
                rule_id=self.id,
                finding_type="skill_count",
                value=len(context.graph.skills()),
                confidence=1.0,
            )
        ]


class DummyRuleC(Rule):
    id = "rule_c"
    name = "Rule C"
    description = "Third test rule, depends on B"
    dependencies = ["rule_b"]

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        return []


class DummyRuleEmpty(Rule):
    id = "rule_empty"
    name = "Empty Rule"
    description = "Produces no results"

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        return []


class DummyRuleError(Rule):
    id = "rule_error"
    name = "Error Rule"
    description = "Always raises"

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        msg = "Intentional test failure"
        raise RuntimeError(msg)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _minimal_graph() -> KnowledgeGraph:
    return KnowledgeGraphBuilder().build(
        {
            "profileVersion": "1.0.0",
            "person": {"id": "person-test"},
            "experiences": [],
            "skills": [],
            "education": [],
            "organizations": [],
            "professionalSummaries": [],
            "projects": [],
            "achievements": [],
            "evidence": [],
            "certifications": [],
            "artifacts": [],
            "targetContexts": [],
        }
    )


def _profile_with_data() -> dict:
    return {
        "profileVersion": "1.0.0",
        "person": {
            "id": "person-raul",
            "names": [{"value": "Raul Gongora", "usage": "professional"}],
        },
        "experiences": [
            {
                "id": "exp-1",
                "title": "Engineer",
                "organizationRefs": [{"id": "org-1", "type": "organization"}],
            }
        ],
        "skills": [
            {"id": "skill-py", "name": "Python", "extensions": {}},
            {"id": "skill-k8s", "name": "Kubernetes", "extensions": {}},
        ],
        "education": [],
        "organizations": [{"id": "org-1", "name": "Corp"}],
        "professionalSummaries": [],
        "projects": [],
        "achievements": [],
        "evidence": [],
        "certifications": [],
        "artifacts": [],
        "targetContexts": [],
    }


# ===================================================================
# ReasoningResult
# ===================================================================


def test_reasoning_result_immutable() -> None:
    r = ReasoningResult(
        rule_id="r1", finding_type="count", value=5, confidence=0.9
    )
    assert r.rule_id == "r1"
    assert r.finding_type == "count"
    assert r.value == 5
    assert r.confidence == 0.9
    assert r.evidence_refs == ()
    assert r.metadata == {}


# ===================================================================
# Evidence
# ===================================================================


def test_evidence_immutable() -> None:
    e = Evidence(id="e1", type="skill", source="rule_a", summary="Python used")
    assert e.id == "e1"
    assert e.type == "skill"
    assert e.source == "rule_a"
    assert e.summary == "Python used"


# ===================================================================
# EvidenceSet
# ===================================================================


def test_evidence_set_empty() -> None:
    s = EvidenceSet(theme="skills")
    assert s.theme == "skills"
    assert s.evidence == ()
    assert s.findings == ()


def test_evidence_set_with_data() -> None:
    e = Evidence(id="e1", type="skill", source="r", summary="s")
    f = ReasoningResult(rule_id="r", finding_type="t", value=1, confidence=0.5)
    s = EvidenceSet(theme="skills", evidence=(e,), findings=(f,))
    assert len(s.evidence) == 1
    assert len(s.findings) == 1


# ===================================================================
# EvidencePackage
# ===================================================================


def test_evidence_package_defaults() -> None:
    p = EvidencePackage()
    assert p.meta == {}
    assert p.candidate_summary == {}
    assert p.relevant_experiences == ()
    assert p.matching_skills == ()
    assert p.education == ()
    assert p.strengths == ()
    assert p.weaknesses == ()
    assert p.missing_competencies == ()
    assert p.supporting_evidence == ()
    assert p.recommendations == ()
    assert p.rule_summary == {}


def test_evidence_package_immutable() -> None:
    p = EvidencePackage(meta={"version": "1"})
    with pytest.raises(AttributeError):
        p.meta = {}  # type: ignore[misc]


# ===================================================================
# RuleContext
# ===================================================================


def test_rule_context() -> None:
    g = _minimal_graph()
    ctx = RuleContext(graph=g, profile={"key": "val"}, parameters={"p": 1})
    assert ctx.graph is g
    assert ctx.profile == {"key": "val"}
    assert ctx.parameters == {"p": 1}


# ===================================================================
# AnalysisModel
# ===================================================================


def test_analysis_model_defaults() -> None:
    now = datetime.now(timezone.utc)
    am = AnalysisModel(profile_id="p1", generated_at=now)
    assert am.profile_id == "p1"
    assert am.generated_at == now
    assert am.reasoning_results == ()
    assert am.evidence == ()
    assert am.evidence_sets == ()
    assert am.execution_stats == {}


def test_analysis_model_immutable() -> None:
    now = datetime.now(timezone.utc)
    am = AnalysisModel(profile_id="p1", generated_at=now)
    with pytest.raises(AttributeError):
        am.profile_id = "p2"  # type: ignore[misc]


# ===================================================================
# RuleRegistry — registration
# ===================================================================


def test_registry_register_and_get() -> None:
    reg = RuleRegistry()
    rule = DummyRuleA()
    reg.register(rule)
    assert reg.get("rule_a") is rule


def test_registry_register_duplicate_raises() -> None:
    reg = RuleRegistry()
    reg.register(DummyRuleA())
    with pytest.raises(DuplicateRuleError, match="already registered"):
        reg.register(DummyRuleA())


def test_registry_unregister() -> None:
    reg = RuleRegistry()
    reg.register(DummyRuleA())
    reg.unregister("rule_a")
    assert reg.get("rule_a") is None


def test_registry_unregister_nonexistent() -> None:
    reg = RuleRegistry()
    reg.unregister("ghost")  # should not raise


def test_registry_list_empty() -> None:
    reg = RuleRegistry()
    assert reg.list() == []


def test_registry_list_returns_all() -> None:
    reg = RuleRegistry()
    reg.register(DummyRuleA())
    reg.register(DummyRuleB())
    assert len(reg.list()) == 2


# ===================================================================
# RuleRegistry — dependency validation
# ===================================================================


def test_registry_validate_dependencies_passes() -> None:
    reg = RuleRegistry()
    reg.register(DummyRuleA())
    reg.register(DummyRuleB())
    reg.validate_dependencies()  # should not raise


def test_registry_validate_dependencies_missing() -> None:
    reg = RuleRegistry()
    reg.register(DummyRuleB())  # depends on rule_a which is not registered
    with pytest.raises(MissingDependencyError, match="depends on 'rule_a'"):
        reg.validate_dependencies()


def test_registry_validate_dependencies_no_deps() -> None:
    reg = RuleRegistry()
    reg.register(DummyRuleA())
    reg.validate_dependencies()  # should not raise


# ===================================================================
# RuleRegistry — execution ordering (topological sort)
# ===================================================================


def test_execution_order_single() -> None:
    reg = RuleRegistry()
    reg.register(DummyRuleA())
    order = reg.execution_order()
    assert len(order) == 1
    assert order[0].id == "rule_a"


def test_execution_order_linear() -> None:
    reg = RuleRegistry()
    reg.register(DummyRuleA())
    reg.register(DummyRuleB())  # depends on A
    reg.register(DummyRuleC())  # depends on B
    order = reg.execution_order()
    ids = [r.id for r in order]
    assert ids == ["rule_a", "rule_b", "rule_c"]


def test_execution_order_independent() -> None:
    reg = RuleRegistry()
    reg.register(DummyRuleB())  # depends on A, but A must still come first
    reg.register(DummyRuleA())
    order = reg.execution_order()
    ids = [r.id for r in order]
    assert ids.index("rule_a") < ids.index("rule_b")


def test_execution_order_no_deps_preserves_insertion() -> None:
    reg = RuleRegistry()
    a = DummyRuleA()
    empty = DummyRuleEmpty()
    reg.register(a)
    reg.register(empty)
    order = reg.execution_order()
    assert order == [a, empty]


def test_execution_order_empty_registry() -> None:
    reg = RuleRegistry()
    assert reg.execution_order() == []


# ===================================================================
# RuleRegistry — circular dependency detection
# ===================================================================


def test_circular_dependency_direct() -> None:
    class SelfDep(Rule):
        id = "self_dep"
        name = "Self"
        description = "Depends on itself"
        dependencies = ["self_dep"]

        def execute(self, context: RuleContext) -> list[ReasoningResult]:
            return []

    reg = RuleRegistry()
    reg.register(SelfDep())
    with pytest.raises(CircularDependencyError):
        reg.execution_order()


def test_circular_dependency_indirect() -> None:
    class X(Rule):
        id = "x"
        name = "X"
        description = ""
        dependencies = ["y"]

        def execute(self, context: RuleContext) -> list[ReasoningResult]:
            return []

    class Y(Rule):
        id = "y"
        name = "Y"
        description = ""
        dependencies = ["x"]

        def execute(self, context: RuleContext) -> list[ReasoningResult]:
            return []

    reg = RuleRegistry()
    reg.register(X())
    reg.register(Y())
    with pytest.raises(CircularDependencyError):
        reg.execution_order()


def test_circular_dependency_longer_chain() -> None:
    class A(Rule):
        id = "a"
        name = "A"
        description = ""
        dependencies = ["b"]

        def execute(self, context: RuleContext) -> list[ReasoningResult]:
            return []

    class B(Rule):
        id = "b"
        name = "B"
        description = ""
        dependencies = ["c"]

        def execute(self, context: RuleContext) -> list[ReasoningResult]:
            return []

    class C(Rule):
        id = "c"
        name = "C"
        description = ""
        dependencies = ["a"]

        def execute(self, context: RuleContext) -> list[ReasoningResult]:
            return []

    reg = RuleRegistry()
    reg.register(A())
    reg.register(B())
    reg.register(C())
    with pytest.raises(CircularDependencyError):
        reg.execution_order()


# ===================================================================
# ReasoningEngine
# ===================================================================


def test_engine_empty_registry() -> None:
    reg = RuleRegistry()
    engine = ReasoningEngine(reg)
    graph = _minimal_graph()
    analysis = engine.run(graph, profile={"person": {"id": "p1"}})
    assert analysis.profile_id == "p1"
    assert analysis.reasoning_results == ()
    assert analysis.execution_stats["total_rules"] == 0


def test_engine_executes_rules() -> None:
    reg = RuleRegistry()
    reg.register(DummyRuleA())
    engine = ReasoningEngine(reg)
    graph = _minimal_graph()
    analysis = engine.run(graph, profile={"person": {"id": "p1"}})
    assert len(analysis.reasoning_results) == 1
    assert analysis.reasoning_results[0].rule_id == "rule_a"
    assert analysis.reasoning_results[0].finding_type == "experience_count"
    assert analysis.reasoning_results[0].value == 0


def test_engine_executes_in_dependency_order() -> None:
    reg = RuleRegistry()
    reg.register(DummyRuleB())  # depends on A
    reg.register(DummyRuleA())
    engine = ReasoningEngine(reg)
    graph = _minimal_graph()
    analysis = engine.run(graph)
    executed = analysis.execution_stats["rules_executed"]
    assert executed == ["rule_a", "rule_b"]


def test_engine_collects_results_from_all_rules() -> None:
    reg = RuleRegistry()
    reg.register(DummyRuleA())
    reg.register(DummyRuleB())
    reg.register(DummyRuleEmpty())
    engine = ReasoningEngine(reg)
    graph = _minimal_graph()
    analysis = engine.run(graph)
    assert len(analysis.reasoning_results) == 2  # A + B produce results; Empty produces none
    assert analysis.execution_stats["total_rules"] == 3
    assert analysis.execution_stats["total_findings"] == 2


def test_engine_deterministic_execution() -> None:
    """Two runs with same graph produce identical results."""
    reg = RuleRegistry()
    reg.register(DummyRuleA())
    engine = ReasoningEngine(reg)
    graph = _minimal_graph()
    analysis1 = engine.run(graph)
    analysis2 = engine.run(graph)
    assert analysis1.reasoning_results == analysis2.reasoning_results
    assert analysis1.execution_stats["rules_executed"] == analysis2.execution_stats["rules_executed"]


def test_engine_uses_profile_data() -> None:
    reg = RuleRegistry()
    reg.register(DummyRuleA())
    engine = ReasoningEngine(reg)
    graph = _minimal_graph()
    profile = _profile_with_data()
    analysis = engine.run(graph, profile=profile)
    assert analysis.profile_id == "person-raul"


def test_engine_resolves_unknown_profile_id() -> None:
    reg = RuleRegistry()
    engine = ReasoningEngine(reg)
    graph = _minimal_graph()
    analysis = engine.run(graph)
    assert analysis.profile_id == "unknown"


def test_engine_rule_error_does_not_affect_other_rules() -> None:
    reg = RuleRegistry()
    reg.register(DummyRuleA())
    reg.register(DummyRuleError())
    engine = ReasoningEngine(reg)
    graph = _minimal_graph()
    with pytest.raises(RuntimeError, match="Intentional test failure"):
        engine.run(graph)


def test_engine_stores_execution_stats() -> None:
    reg = RuleRegistry()
    reg.register(DummyRuleA())
    engine = ReasoningEngine(reg)
    graph = _minimal_graph()
    analysis = engine.run(graph)
    stats = analysis.execution_stats
    assert "total_rules" in stats
    assert "total_findings" in stats
    assert "execution_time_seconds" in stats
    assert "rules_executed" in stats
    assert "findings_per_rule" in stats
    assert "started_at" in stats
    assert "completed_at" in stats
    assert stats["total_rules"] == 1
    assert stats["total_findings"] == 1


# ===================================================================
# EvidencePackageAssembler
# ===================================================================


def test_assembler_empty_analysis() -> None:
    now = datetime.now(timezone.utc)
    analysis = AnalysisModel(profile_id="p1", generated_at=now)
    assembler = EvidencePackageAssembler()
    pkg = assembler.assemble(analysis)
    assert pkg.meta["profile_id"] == "p1"
    assert pkg.relevant_experiences == ()
    assert pkg.matching_skills == ()
    assert pkg.strengths == ()
    assert pkg.weaknesses == ()


def test_assembler_sections_results_by_finding_type() -> None:
    now = datetime.now(timezone.utc)
    results = [
        ReasoningResult(rule_id="r1", finding_type="experience_count", value=3, confidence=0.9),
        ReasoningResult(rule_id="r2", finding_type="skill_count", value=5, confidence=0.8),
        ReasoningResult(rule_id="r3", finding_type="strength_leadership", value=True, confidence=0.7),
        ReasoningResult(rule_id="r4", finding_type="weakness_management", value=True, confidence=0.6),
        ReasoningResult(rule_id="r5", finding_type="gap_cloud", value="AWS", confidence=0.5),
        ReasoningResult(rule_id="r6", finding_type="recommendation_upskill", value="Kubernetes", confidence=0.9),
    ]
    analysis = AnalysisModel(
        profile_id="p1",
        generated_at=now,
        reasoning_results=tuple(results),
        execution_stats={"total_rules": 6, "total_findings": 6, "execution_time_seconds": 0.1},
    )
    assembler = EvidencePackageAssembler()
    pkg = assembler.assemble(analysis)

    assert len(pkg.relevant_experiences) == 1
    assert pkg.relevant_experiences[0]["finding_type"] == "experience_count"
    assert len(pkg.matching_skills) == 1
    assert pkg.matching_skills[0]["finding_type"] == "skill_count"
    assert len(pkg.strengths) == 1
    assert pkg.strengths[0]["finding_type"] == "strength_leadership"
    assert len(pkg.weaknesses) == 1
    assert pkg.weaknesses[0]["finding_type"] == "weakness_management"
    assert len(pkg.missing_competencies) == 1
    assert pkg.missing_competencies[0]["finding_type"] == "gap_cloud"
    assert len(pkg.recommendations) == 1
    assert pkg.recommendations[0]["finding_type"] == "recommendation_upskill"


def test_assembler_populates_supporting_evidence() -> None:
    now = datetime.now(timezone.utc)
    results = [
        ReasoningResult(rule_id="r1", finding_type="experience_count", value=3, confidence=0.9),
    ]
    analysis = AnalysisModel(
        profile_id="p1",
        generated_at=now,
        reasoning_results=tuple(results),
        execution_stats={"total_rules": 1, "total_findings": 1, "execution_time_seconds": 0.01},
    )
    assembler = EvidencePackageAssembler()
    pkg = assembler.assemble(analysis)
    assert len(pkg.supporting_evidence) == 1
    assert pkg.supporting_evidence[0]["evidence_id"] == "r1-experience_count"
    assert pkg.supporting_evidence[0]["source"] == "r1"


def test_assembler_populates_candidate_summary() -> None:
    now = datetime.now(timezone.utc)
    results = [
        ReasoningResult(rule_id="r1", finding_type="total_years_of_experience", value=8.5, confidence=0.9),
        ReasoningResult(rule_id="r2", finding_type="highest_education", value="M.Sc.", confidence=1.0),
        ReasoningResult(rule_id="r3", finding_type="career_stage_classification", value="Senior", confidence=0.8),
    ]
    analysis = AnalysisModel(
        profile_id="p1",
        generated_at=now,
        reasoning_results=tuple(results),
        execution_stats={"total_rules": 3, "total_findings": 3, "execution_time_seconds": 0.01},
    )
    assembler = EvidencePackageAssembler()
    pkg = assembler.assemble(analysis)
    assert pkg.candidate_summary["total_years_of_experience"] == 8.5
    assert pkg.candidate_summary["highest_education"] == "M.Sc."
    assert pkg.candidate_summary["career_stage"] == "Senior"
    assert pkg.candidate_summary["total_findings"] == 3


def test_assembler_populates_rule_summary() -> None:
    now = datetime.now(timezone.utc)
    analysis = AnalysisModel(
        profile_id="p1",
        generated_at=now,
        execution_stats={
            "total_rules": 5,
            "total_findings": 12,
            "execution_time_seconds": 0.05,
        },
    )
    assembler = EvidencePackageAssembler()
    pkg = assembler.assemble(analysis)
    assert pkg.rule_summary["total_rules_executed"] == 5
    assert pkg.rule_summary["total_findings_produced"] == 12
    assert pkg.rule_summary["execution_time_seconds"] == 0.05


def test_assembler_provides_reasoning_version() -> None:
    now = datetime.now(timezone.utc)
    analysis = AnalysisModel(profile_id="p1", generated_at=now)
    assembler = EvidencePackageAssembler()
    pkg = assembler.assemble(analysis)
    assert pkg.meta["reasoning_version"] == "1.0.0"


def test_assembler_unknown_finding_type_goes_to_supporting_evidence_only() -> None:
    now = datetime.now(timezone.utc)
    results = [
        ReasoningResult(rule_id="r1", finding_type="custom_unmapped", value="x", confidence=0.5),
    ]
    analysis = AnalysisModel(
        profile_id="p1",
        generated_at=now,
        reasoning_results=tuple(results),
        execution_stats={"total_rules": 1, "total_findings": 1, "execution_time_seconds": 0.01},
    )
    assembler = EvidencePackageAssembler()
    pkg = assembler.assemble(analysis)
    assert pkg.relevant_experiences == ()
    assert pkg.matching_skills == ()
    assert len(pkg.supporting_evidence) == 1


# ===================================================================
# Integration: Registry → Engine → Assembler
# ===================================================================


def test_full_pipeline() -> None:
    reg = RuleRegistry()
    reg.register(DummyRuleA())
    reg.register(DummyRuleB())
    engine = ReasoningEngine(reg)
    graph = KnowledgeGraphBuilder().build(_profile_with_data())
    analysis = engine.run(graph, profile=_profile_with_data())
    assert analysis.profile_id == "person-raul"
    assert len(analysis.reasoning_results) == 2

    assembler = EvidencePackageAssembler()
    pkg = assembler.assemble(analysis)
    assert pkg.meta["profile_id"] == "person-raul"
    # DummyRuleA finding_type = "experience_count" → relevant_experiences
    assert len(pkg.relevant_experiences) == 1
    assert pkg.relevant_experiences[0]["value"] == 1  # one experience in profile
    # DummyRuleB finding_type = "skill_count" → matching_skills
    assert len(pkg.matching_skills) == 1
    assert pkg.matching_skills[0]["value"] == 2  # two skills in profile


def test_full_pipeline_deterministic() -> None:
    reg = RuleRegistry()
    reg.register(DummyRuleA())
    engine = ReasoningEngine(reg)
    graph = KnowledgeGraphBuilder().build(_profile_with_data())
    pkg1 = EvidencePackageAssembler().assemble(engine.run(graph))
    pkg2 = EvidencePackageAssembler().assemble(engine.run(graph))
    assert pkg1 == pkg2


def test_registry_preserves_order_across_operations() -> None:
    reg = RuleRegistry()
    reg.register(DummyRuleB())  # depends on A
    reg.register(DummyRuleA())
    reg.register(DummyRuleEmpty())
    order1 = [r.id for r in reg.execution_order()]
    # Re-register A (should fail), unregister empty, re-register
    with pytest.raises(DuplicateRuleError):
        reg.register(DummyRuleA())
    reg.unregister("rule_empty")
    order2 = [r.id for r in reg.execution_order()]
    assert order2 == ["rule_a", "rule_b"]
    # Ensure order is still valid even after modify
    assert order2.index("rule_a") < order2.index("rule_b")


# ===================================================================
# Immutability enforcement
# ===================================================================


def test_evidence_package_uses_tuples_not_lists() -> None:
    pkg = EvidencePackage(meta={"v": "1"})
    assert isinstance(pkg.relevant_experiences, tuple)
    assert isinstance(pkg.matching_skills, tuple)
    assert isinstance(pkg.supporting_evidence, tuple)


def test_analysis_model_uses_tuples_not_lists() -> None:
    now = datetime.now(timezone.utc)
    am = AnalysisModel(profile_id="p1", generated_at=now)
    assert isinstance(am.reasoning_results, tuple)
    assert isinstance(am.evidence, tuple)


def test_reasoning_result_immutable_fields() -> None:
    r = ReasoningResult(rule_id="r1", finding_type="t", value=1, confidence=0.5)
    with pytest.raises(AttributeError):
        r.rule_id = "r2"  # type: ignore[misc]


# ===================================================================
# ReasoningReport
# ===================================================================


def test_reasoning_report_defaults() -> None:
    report = ReasoningReport()
    assert report.engine_version == "1.0.0"
    assert report.profile_id == "unknown"
    assert report.findings == ()
    assert report.findings_by_type == {}
    assert report.summary == {}
    assert report.execution_stats == {}


def test_reasoning_report_immutable() -> None:
    report = ReasoningReport()
    with pytest.raises(AttributeError):
        report.profile_id = "p2"  # type: ignore[misc]


def test_reasoning_report_to_dict() -> None:
    r = ReasoningResult(
        rule_id="r1",
        finding_type="test_type",
        value=42,
        confidence=0.95,
        evidence_refs=("ref-a",),
        metadata={"source": "test"},
    )
    report = ReasoningReport(
        profile_id="person-abc",
        findings=(r,),
        findings_by_type={"test_type": (r,)},
        summary={"total_findings": 1, "total_rules_executed": 1},
        execution_stats={"total_rules": 1, "total_findings": 1},
    )
    d = report.to_dict()
    assert d["engine_version"] == "1.0.0"
    assert d["profile_id"] == "person-abc"
    assert len(d["findings"]) == 1
    assert d["findings"][0]["rule_id"] == "r1"
    assert d["findings"][0]["finding_type"] == "test_type"
    assert d["findings"][0]["value"] == 42
    assert d["findings"][0]["confidence"] == 0.95
    assert d["findings"][0]["evidence_refs"] == ["ref-a"]
    assert d["findings"][0]["metadata"] == {"source": "test"}
    assert "test_type" in d["findings_by_type"]
    assert len(d["findings_by_type"]["test_type"]) == 1
    assert d["summary"]["total_findings"] == 1
    assert "execution_time_seconds" in d["execution_stats"] or d["execution_stats"]["total_rules"] == 1


def test_reasoning_report_to_json() -> None:
    r = ReasoningResult(rule_id="r1", finding_type="t", value=1, confidence=0.5)
    report = ReasoningReport(
        profile_id="p1",
        findings=(r,),
        findings_by_type={"t": (r,)},
        summary={"total_findings": 1},
    )
    raw = report.to_json()
    import json

    parsed = json.loads(raw)
    assert parsed["profile_id"] == "p1"
    assert len(parsed["findings"]) == 1
    assert parsed["findings"][0]["rule_id"] == "r1"


def test_reasoning_report_to_json_indent() -> None:
    report = ReasoningReport(profile_id="p1")
    raw_indent = report.to_json(indent=4)
    raw_default = report.to_json()
    assert '"profile_id": "p1"' in raw_indent
    assert len(raw_indent) > len(raw_default)


def test_reasoning_report_findings_by_type_empty_when_no_findings() -> None:
    report = ReasoningReport(profile_id="p1")
    assert report.to_dict()["findings_by_type"] == {}


def test_reasoning_report_summary_custom_values() -> None:
    report = ReasoningReport(
        profile_id="p1",
        summary={"total_findings": 14, "confidence_distribution": {"1.0": 10, "0.8": 4}},
    )
    assert report.summary["total_findings"] == 14
    assert report.summary["confidence_distribution"]["1.0"] == 10


# ===================================================================
# ReasoningEngine.analyze()
# ===================================================================


class DummyFindingRule(Rule):
    id = "dummy_finding"
    name = "Dummy Finding"
    description = "Produces a single finding for testing analyze()"

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        return [
            ReasoningResult(
                rule_id=self.id,
                finding_type="test_finding",
                value=len(context.graph.experiences()),
                confidence=1.0,
            )
        ]


class DummyMultiRule(Rule):
    id = "dummy_multi"
    name = "Dummy Multi"
    description = "Produces multiple findings"

    def execute(self, context: RuleContext) -> list[ReasoningResult]:
        return [
            ReasoningResult(
                rule_id=self.id, finding_type="type_a", value=1, confidence=1.0
            ),
            ReasoningResult(
                rule_id=self.id, finding_type="type_b", value="x", confidence=0.8
            ),
        ]


def test_engine_analyze_empty_profile() -> None:
    reg = RuleRegistry()
    reg.register(DummyFindingRule())
    engine = ReasoningEngine(reg)
    report = engine.analyze({"person": {"id": "p-empty"}, "experiences": [], "skills": []})
    assert isinstance(report, ReasoningReport)
    assert report.profile_id == "p-empty"
    assert report.engine_version == "1.0.0"
    assert report.summary["total_findings"] == 1
    assert report.findings[0].value == 0


def test_engine_analyze_with_experiences() -> None:
    reg = RuleRegistry()
    reg.register(DummyFindingRule())
    engine = ReasoningEngine(reg)
    profile = {
        "profileVersion": "1.0.0",
        "person": {"id": "person-exp"},
        "experiences": [
            {
                "id": "exp-1",
                "title": "Engineer",
                "organizationRefs": [{"id": "org-1"}],
            }
        ],
        "skills": [],
        "education": [],
        "organizations": [{"id": "org-1", "name": "Corp"}],
        "professionalSummaries": [],
        "projects": [],
        "achievements": [],
        "evidence": [],
        "certifications": [],
        "artifacts": [],
        "targetContexts": [],
    }
    report = engine.analyze(profile)
    assert report.profile_id == "person-exp"
    assert len(report.findings) == 1
    assert report.findings[0].value == 1


def test_engine_analyze_findings_by_type() -> None:
    reg = RuleRegistry()
    reg.register(DummyMultiRule())
    engine = ReasoningEngine(reg)
    report = engine.analyze(
        {"person": {"id": "p"}, "experiences": [], "skills": []}
    )
    assert "type_a" in report.findings_by_type
    assert "type_b" in report.findings_by_type
    assert len(report.findings_by_type["type_a"]) == 1
    assert len(report.findings_by_type["type_b"]) == 1
    assert report.findings_by_type["type_a"][0].finding_type == "type_a"
    assert report.findings_by_type["type_b"][0].finding_type == "type_b"


def test_engine_analyze_summary() -> None:
    reg = RuleRegistry()
    reg.register(DummyMultiRule())
    engine = ReasoningEngine(reg)
    report = engine.analyze(
        {"person": {"id": "p"}, "experiences": [], "skills": []}
    )
    assert report.summary["total_findings"] == 2
    assert report.summary["findings_by_type_count"]["type_a"] == 1
    assert report.summary["findings_by_type_count"]["type_b"] == 1
    assert report.summary["total_rules_executed"] == 1
    assert "confidence_distribution" in report.summary
    assert report.summary["confidence_distribution"]["1.0"] == 1
    assert report.summary["confidence_distribution"]["0.8"] == 1
    assert report.summary["execution_time_seconds"] >= 0


def test_engine_analyze_execution_stats() -> None:
    reg = RuleRegistry()
    reg.register(DummyFindingRule())
    engine = ReasoningEngine(reg)
    report = engine.analyze(
        {"person": {"id": "p"}, "experiences": [], "skills": []}
    )
    stats = report.execution_stats
    assert "total_rules" in stats
    assert "total_findings" in stats
    assert "execution_time_seconds" in stats
    assert "rules_executed" in stats
    assert "findings_per_rule" in stats
    assert stats["total_rules"] == 1
    assert stats["total_findings"] == 1


def test_engine_analyze_deterministic() -> None:
    reg = RuleRegistry()
    reg.register(DummyFindingRule())
    engine = ReasoningEngine(reg)
    profile = {"person": {"id": "p"}, "experiences": [], "skills": []}
    report1 = engine.analyze(profile)
    report2 = engine.analyze(profile)
    assert _deterministic_payload(report1) == _deterministic_payload(report2)


def _deterministic_payload(report: ReasoningReport) -> dict[str, Any]:
    """Strip runtime-only metadata so determinism asserts semantic output only.

    ``generated_at`` and timing statistics vary between executions; all other
    computed content must remain byte-identical (see test_profile_quality).
    """
    payload = copy.deepcopy(report.to_dict())
    payload.pop("generated_at", None)
    payload.get("execution_stats", {}).pop("started_at", None)
    payload.get("execution_stats", {}).pop("completed_at", None)
    payload.get("execution_stats", {}).pop("execution_time_seconds", None)
    payload.get("summary", {}).pop("execution_time_seconds", None)
    return payload


def test_engine_analyze_serialization_roundtrip() -> None:
    reg = RuleRegistry()
    reg.register(DummyMultiRule())
    engine = ReasoningEngine(reg)
    report = engine.analyze(
        {"person": {"id": "p-roundtrip"}, "experiences": [], "skills": []}
    )
    import json

    raw = report.to_json()
    parsed = json.loads(raw)
    assert parsed["profile_id"] == "p-roundtrip"
    assert parsed["engine_version"] == "1.0.0"
    assert len(parsed["findings"]) == 2
    assert len(parsed["findings_by_type"]) == 2
    assert parsed["summary"]["total_findings"] == 2
    assert "execution_time_seconds" in parsed["execution_stats"]


def test_engine_analyze_no_rules_produces_empty() -> None:
    reg = RuleRegistry()
    engine = ReasoningEngine(reg)
    report = engine.analyze(
        {"person": {"id": "p"}, "experiences": [], "skills": []}
    )
    assert report.findings == ()
    assert report.findings_by_type == {}
    assert report.summary["total_findings"] == 0
    assert report.summary["total_rules_executed"] == 0


def test_engine_analyze_multiple_rules_summary_counts() -> None:
    reg = RuleRegistry()
    reg.register(DummyFindingRule())
    reg.register(DummyMultiRule())
    engine = ReasoningEngine(reg)
    report = engine.analyze(
        {"person": {"id": "p"}, "experiences": [], "skills": []}
    )
    assert report.summary["total_rules_executed"] == 2
    assert report.summary["total_findings"] == 3


def test_engine_run_still_works_unchanged() -> None:
    reg = RuleRegistry()
    reg.register(DummyFindingRule())
    engine = ReasoningEngine(reg)
    g = KnowledgeGraphBuilder().build({"person": {"id": "p"}, "experiences": [], "skills": []})
    analysis = engine.run(g, profile={"person": {"id": "p"}})
    assert isinstance(analysis, AnalysisModel)
    assert analysis.profile_id == "p"
    assert len(analysis.reasoning_results) == 1
