"""Unit tests for CSKS knowledge extractors (M1.22)."""

from __future__ import annotations

from pathlib import Path

import pytest

from careeros.csks.extractor import (
    GitTagExtractor,
    JSONSchemaExtractor,
    MarkdownExtractor,
    PythonASTExtractor,
    YAMLTOMLConfigExtractor,
    get_all_extractors,
)


@pytest.fixture
def py_extractor(csks_sample_repo: Path) -> PythonASTExtractor:
    return PythonASTExtractor(csks_sample_repo)


@pytest.fixture
def md_extractor(csks_sample_repo: Path) -> MarkdownExtractor:
    return MarkdownExtractor(csks_sample_repo)


def _by_type(entities, entity_type: str):
    return [e for e in entities if e.entity_type == entity_type]


def test_python_extractor_can_extract_py(py_extractor: PythonASTExtractor) -> None:
    assert py_extractor.can_extract("careeros/widgets.py") is True
    assert py_extractor.can_extract("docs/architecture/02-domain-map.md") is False


def test_python_extractor_classifies_component(py_extractor: PythonASTExtractor) -> None:
    entities = list(py_extractor.extract_entities("careeros/widgets.py"))
    components = _by_type(entities, "component")
    ids = {e.id for e in components}
    assert "component.careeros.widgets.ConcreteWidget" in ids
    assert "component.careeros.widgets.make_widget" in ids


def test_python_extractor_classifies_rule(py_extractor: PythonASTExtractor) -> None:
    entities = list(py_extractor.extract_entities("careeros/reasoning/rules/skill_rules.py"))
    rules = _by_type(entities, "rule")
    assert any(e.id == "rule.total_years_experience" for e in rules)
    assert not any(e.id.endswith("Rule") for e in rules)


def test_python_extractor_classifies_generator(py_extractor: PythonASTExtractor) -> None:
    entities = list(py_extractor.extract_entities("careeros/generators/markdown_generator.py"))
    generators = _by_type(entities, "generator")
    assert any(e.id == "generator.markdown" for e in generators)


def test_python_extractor_extracts_api_endpoints(py_extractor: PythonASTExtractor) -> None:
    entities = list(py_extractor.extract_entities("api/main.py"))
    endpoints = _by_type(entities, "api_endpoint")
    ids = {e.id for e in endpoints}
    assert "api.get.profiles" in ids
    assert "api.get.profiles.profile_id" in ids
    for ep in endpoints:
        assert ep.properties["path"].startswith("/")


def test_python_extractor_extracts_cli_commands(py_extractor: PythonASTExtractor) -> None:
    entities = list(py_extractor.extract_entities("careeros_cli/main.py"))
    commands = _by_type(entities, "cli_command")
    ids = {e.id for e in commands}
    assert "cli.version" in ids
    assert "cli.validate" in ids


def test_python_extractor_extracts_dependencies(py_extractor: PythonASTExtractor) -> None:
    entities = list(py_extractor.extract_entities("careeros/profile_loader.py"))
    deps = _by_type(entities, "dependency")
    assert any(d.properties.get("imported_name") == "ConcreteWidget" for d in deps)


def test_python_extractor_extracts_import_relationships(py_extractor: PythonASTExtractor) -> None:
    rels = list(py_extractor.extract_relationships("careeros/profile_loader.py"))
    import_edges = [r for r in rels if r.properties.get("type") == "import"]
    assert any(
        r.to_id == "component.careeros.widgets.ConcreteWidget"
        and r.from_id.startswith("dependency.careeros.profile_loader.")
        for r in import_edges
    )


def test_python_extractor_extracts_call_relationships(py_extractor: PythonASTExtractor) -> None:
    rels = list(py_extractor.extract_relationships("careeros/profile_loader.py"))
    call_edges = [r for r in rels if r.properties.get("type") == "function_call"]
    assert any(
        r.from_id == "component.careeros.profile_loader.load_default_profile"
        and r.to_id == "component.careeros.profile_loader.make_widget"
        for r in call_edges
    )


def test_python_extractor_handles_syntax_errors(py_extractor: PythonASTExtractor, csks_sample_repo: Path) -> None:
    bad = csks_sample_repo / "careeros" / "broken.py"
    bad.write_text("def broken(:\n", encoding="utf-8")
    rel_path = "careeros/broken.py"
    assert list(py_extractor.extract_entities(rel_path)) == []
    assert list(py_extractor.extract_relationships(rel_path)) == []


def test_markdown_extractor_extracts_domains(md_extractor: MarkdownExtractor) -> None:
    entities = list(md_extractor.extract_entities("docs/architecture/02-domain-map.md"))
    domains = _by_type(entities, "domain")
    ids = {e.id for e in domains}
    assert "domain.profile_management" in ids
    assert "domain.knowledge_graph" in ids
    assert "domain.schema_foundation" in ids


def test_markdown_extractor_extracts_domain_relationships(md_extractor: MarkdownExtractor) -> None:
    rels = list(md_extractor.extract_relationships("docs/architecture/02-domain-map.md"))
    domain_edges = [r for r in rels if r.properties.get("type") == "domain_dependency"]
    assert ("domain.profile_management", "domain.schema_foundation") in {
        (r.from_id, r.to_id) for r in domain_edges
    }
    assert ("domain.knowledge_graph", "domain.profile_management") in {
        (r.from_id, r.to_id) for r in domain_edges
    }


def test_markdown_extractor_extracts_adrs(md_extractor: MarkdownExtractor) -> None:
    entities = list(md_extractor.extract_entities("docs/adr/0001-storage.md"))
    adrs = _by_type(entities, "adr")
    assert len(adrs) == 1
    assert adrs[0].id == "adr.001"
    assert adrs[0].properties["title"] == "Storage Backend"
    assert adrs[0].properties["status"] == "Accepted"


def test_markdown_extractor_extracts_frontmatter_adr(md_extractor: MarkdownExtractor) -> None:
    entities = list(md_extractor.extract_entities("docs/adr/0002-llm.md"))
    adrs = _by_type(entities, "adr")
    assert any(e.id == "adr.002" and e.properties["status"] == "Proposed" for e in adrs)


def test_markdown_extractor_extracts_mermaid_entities(md_extractor: MarkdownExtractor) -> None:
    entities = list(md_extractor.extract_entities("docs/architecture/02-domain-map.md"))
    mermaid = _by_type(entities, "mermaid_edge")
    assert len(mermaid) == 2


def test_markdown_extractor_extracts_mermaid_relationships(md_extractor: MarkdownExtractor) -> None:
    rels = list(md_extractor.extract_relationships("docs/architecture/02-domain-map.md"))
    mermaid = [r for r in rels if r.properties.get("source") == "mermaid"]
    assert len(mermaid) == 2


def test_markdown_extractor_extracts_headings_as_documents(md_extractor: MarkdownExtractor) -> None:
    entities = list(md_extractor.extract_entities("docs/adr/0001-storage.md"))
    docs = _by_type(entities, "document")
    assert any(e.properties.get("title") == "ADR 0001: Storage Backend" for e in docs)

    domain_docs = _by_type(
        list(md_extractor.extract_entities("docs/architecture/02-domain-map.md")),
        "document",
    )
    assert any("domain_map" in e.id for e in domain_docs)
    assert any(e.properties.get("title") == "Domain Map" for e in domain_docs)


def test_markdown_extractor_extracts_table_rows(md_extractor: MarkdownExtractor) -> None:
    entities = list(md_extractor.extract_entities("docs/architecture/02-domain-map.md"))
    rows = _by_type(entities, "table_row")
    assert len(rows) == 2
    assert all(row.properties.get("Status") == "Core" for row in rows)


def test_json_schema_extractor(csks_sample_repo: Path) -> None:
    extractor = JSONSchemaExtractor(csks_sample_repo)
    entities = list(extractor.extract_entities("schemas/skill.schema.json"))
    assert len(entities) == 1
    entity = entities[0]
    assert entity.entity_type == "schema"
    assert entity.id == "schema.skill"
    assert entity.properties["properties"] == ["name", "level"]


def test_json_schema_extractor_ref_relationship(csks_sample_repo: Path) -> None:
    extractor = JSONSchemaExtractor(csks_sample_repo)
    rels = list(extractor.extract_relationships("schemas/role.schema.json"))
    assert ("schema.role", "schema.skill", "depends_on") in {
        (r.from_id, r.to_id, r.relationship_type) for r in rels
    }


def test_yaml_toml_extractor(csks_sample_repo: Path) -> None:
    extractor = YAMLTOMLConfigExtractor(csks_sample_repo)
    entities = list(extractor.extract_entities("pyproject.toml"))
    configs = _by_type(entities, "configuration")
    assert any(c.properties.get("section") == "project" for c in configs)


def test_git_tag_extractor_without_git_repo(csks_sample_repo: Path) -> None:
    extractor = GitTagExtractor(csks_sample_repo)
    assert extractor.can_extract(".") is True
    assert list(extractor.extract_entities(".")) == []


def test_get_all_extractors_priority(csks_sample_repo: Path) -> None:
    extractors = get_all_extractors(csks_sample_repo)
    names = [e.__class__.__name__ for e in extractors]
    assert names == [
        "PythonASTExtractor",
        "MarkdownExtractor",
        "JSONSchemaExtractor",
        "YAMLTOMLConfigExtractor",
        "GitTagExtractor",
    ]


def test_base_extractor_make_citation(py_extractor: PythonASTExtractor) -> None:
    citation = py_extractor._make_citation(
        "careeros/widgets.py",
        line_start=4,
        line_end=4,
        entity_id="component.careeros.widgets.Widget",
    )
    assert citation["file"] == "careeros/widgets.py"
    assert citation["line_start"] == 4
    assert "class Widget" in citation["text"]
    assert citation["entity_id"] == "component.careeros.widgets.Widget"


def test_get_module_name_handles_absolute_path(py_extractor: PythonASTExtractor, csks_sample_repo: Path) -> None:
    absolute = str((csks_sample_repo / "careeros" / "widgets.py").resolve())
    assert py_extractor._get_module_name(absolute) == "careeros.widgets"


def test_classify_class_in_tests_dir(csks_sample_repo: Path) -> None:
    extractor = PythonASTExtractor(csks_sample_repo)
    entities = list(extractor.extract_entities("tests/test_sample.py"))
    components = _by_type(entities, "component")
    assert not components
    tests = _by_type(entities, "test")
    assert any(e.id == "test.tests.test_sample.test_sample" for e in tests)


def test_yaml_config_extractor(csks_sample_repo: Path) -> None:
    (csks_sample_repo / "config.yaml").write_text(
        "service:\n  name: csks\n  port: 8000\n",
        encoding="utf-8",
    )
    extractor = YAMLTOMLConfigExtractor(csks_sample_repo)
    entities = list(extractor.extract_entities("config.yaml"))
    configs = _by_type(entities, "configuration")
    assert any(c.properties.get("key") == "service" for c in configs)


def test_env_config_extractor(csks_sample_repo: Path) -> None:
    (csks_sample_repo / ".env.example").write_text(
        "CSKS_MAX_ENTITIES=5000\n# comment\nCSKS_LOG_LEVEL=info\n",
        encoding="utf-8",
    )
    extractor = YAMLTOMLConfigExtractor(csks_sample_repo)
    entities = list(extractor.extract_entities(".env.example"))
    configs = _by_type(entities, "configuration")
    keys = {c.properties.get("key") for c in configs}
    assert "CSKS_MAX_ENTITIES" in keys
    assert "CSKS_LOG_LEVEL" in keys
    assert len(keys) == 2


def test_git_tag_extractor_with_real_git_repo(csks_sample_repo: Path) -> None:
    import subprocess

    def git(*args: str) -> None:
        subprocess.run(
            ["git", "-C", str(csks_sample_repo), *args],
            check=True,
            capture_output=True,
            text=True,
        )

    git("init", "-q")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test")
    git("add", ".")
    git("commit", "-q", "-m", "initial")
    git("tag", "-a", "m1.22-csks-foundation", "-m", "checkpoint")
    git("tag", "-a", "v1.0.0", "-m", "release")

    extractor = GitTagExtractor(csks_sample_repo)
    entities = list(extractor.extract_entities("."))
    assert any(e.entity_type == "milestone" and e.id == "milestone.m1.22-csks-foundation" for e in entities)
    assert any(e.entity_type == "release" and e.id == "release.v1.0.0" for e in entities)

    rels = list(extractor.extract_relationships("."))
    assert rels == []
