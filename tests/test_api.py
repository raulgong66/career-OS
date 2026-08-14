import pytest

pytest.importorskip("fastapi", reason="fastapi is not installed — API tests require it")

from pathlib import Path

from fastapi.testclient import TestClient
import yaml

from api.main import app


client = TestClient(app)

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_version_endpoint() -> None:
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json()["version"] == "1.0.0"


def test_schemas_endpoint() -> None:
    response = client.get("/schemas")
    assert response.status_code == 200
    assert "profile" in response.json()


def test_validate_endpoint() -> None:
    response = client.post(
        "/validate/profile",
        json={
            "payload": {
                "profileVersion": "1.0.0",
                "person": {
                    "id": "person-1",
                    "names": [{"value": "Jane Doe", "usage": "professional"}],
                    "contact": {"email": "jane@example.com"},
                    "location": {"city": "Stockholm"},
                    "positioning": {
                        "headline": "Product engineer",
                        "valueProposition": "Builds reliable systems",
                        "targetDirection": "Growth",
                        "themes": ["Engineering"],
                    },
                },
            }
        },
    )
    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_create_and_fetch_entity() -> None:
    response = client.post(
        "/entities/company",
        json={
            "id": "company-1",
            "name": "Example company",
            "metadata": {"id": "company-1", "version": "1.0.0", "status": "ACTIVE"},
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["id"] == "company-1"

    fetch_response = client.get("/entities/company/company-1")
    assert fetch_response.status_code == 200
    assert fetch_response.json()["id"] == "company-1"


def test_update_and_delete_entity() -> None:
    create_response = client.post(
        "/entities/company",
        json={
            "id": "company-2",
            "name": "Example company",
            "metadata": {"id": "company-2", "version": "1.0.0", "status": "ACTIVE"},
        },
    )
    assert create_response.status_code == 201

    update_response = client.put(
        "/entities/company/company-2",
        json={"name": "Updated company"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["name"] == "Updated company"

    delete_response = client.delete("/entities/company/company-2")
    assert delete_response.status_code == 204


def test_generate_markdown_cv_endpoint_returns_markdown(tmp_path: Path) -> None:
    profile_file = tmp_path / "profile.yaml"
    profile_file.write_text(
        yaml.safe_dump(
            {
                "profileVersion": "1.0.0",
                "person": {
                    "id": "person-1",
                    "names": [{"value": "Jane Doe", "usage": "professional"}],
                },
                "skills": [{"id": "skill-1", "name": "AI workflow design"}],
                "targetContexts": [{"id": "context-1", "role": "AI Product Engineer"}],
                "artifacts": [
                    {
                        "id": "artifact-1",
                        "title": "AI Platform CV",
                        "artifactType": "CV",
                        "targetContextRefs": [{"id": "context-1", "type": "targetContext"}],
                        "sourceRefs": [{"id": "skill-1", "type": "skill"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    response = client.post(
        "/generate/markdown-cv",
        json={"profile_path": str(profile_file), "artifact_id": "artifact-1"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert "# Jane Doe" in response.text
    assert "AI workflow design" in response.text


def test_generate_markdown_cv_endpoint_reports_missing_artifact(tmp_path: Path) -> None:
    profile_file = tmp_path / "profile.yaml"
    profile_file.write_text(
        yaml.safe_dump(
            {
                "profileVersion": "1.0.0",
                "person": {"id": "person-1"},
                "artifacts": [],
            }
        ),
        encoding="utf-8",
    )

    response = client.post(
        "/generate/markdown-cv",
        json={"profile_path": str(profile_file), "artifact_id": "missing"},
    )

    assert response.status_code == 404
    assert "Artifact not found" in response.json()["detail"]


def test_generate_artifact_endpoint_returns_markdown(tmp_path: Path) -> None:
    profile_file = tmp_path / "profile.yaml"
    profile_file.write_text(
        yaml.safe_dump(
            {
                "profileVersion": "1.0.0",
                "person": {"id": "person-1", "names": [{"value": "Jane Doe"}]},
                "skills": [{"id": "skill-1", "name": "AI workflow design"}],
                "artifacts": [
                    {
                        "id": "artifact-1",
                        "artifactType": "CV",
                        "sourceRefs": [{"id": "skill-1", "type": "skill"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    response = client.post(
        "/generate/artifact",
        json={"profile_path": str(profile_file), "artifact_id": "artifact-1", "output_format": "markdown"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert "# Jane Doe" in response.text
    assert "AI workflow design" in response.text


def test_generate_artifact_endpoint_returns_docx(tmp_path: Path) -> None:
    profile_file = tmp_path / "profile.yaml"
    profile_file.write_text(
        yaml.safe_dump(
            {
                "profileVersion": "1.0.0",
                "person": {"id": "person-1", "names": [{"value": "Jane Doe"}]},
                "skills": [{"id": "skill-1", "name": "AI workflow design"}],
                "artifacts": [
                    {
                        "id": "artifact-1",
                        "artifactType": "CV",
                        "sourceRefs": [{"id": "skill-1", "type": "skill"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    response = client.post(
        "/generate/artifact",
        json={"profile_path": str(profile_file), "artifact_id": "artifact-1", "output_format": "docx"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert response.content.startswith(b"PK")


def test_generate_artifact_endpoint_reports_unregistered_format(tmp_path: Path) -> None:
    profile_file = tmp_path / "profile.yaml"
    profile_file.write_text(
        yaml.safe_dump(
            {
                "profileVersion": "1.0.0",
                "person": {"id": "person-1"},
                "artifacts": [{"id": "artifact-1", "artifactType": "CV"}],
            }
        ),
        encoding="utf-8",
    )

    response = client.post(
        "/generate/artifact",
        json={"profile_path": str(profile_file), "artifact_id": "artifact-1", "output_format": "html"},
    )

    assert response.status_code == 422
    assert "No generator registered" in response.json()["detail"]


def test_list_profiles_endpoint() -> None:
    response = client.get("/profiles")
    assert response.status_code == 200
    profiles = response.json()
    assert isinstance(profiles, list)
    assert len(profiles) >= 1
    ids = [p["id"] for p in profiles]
    assert "raul-gongora-profile" in ids
    raul = next(p for p in profiles if p["id"] == "raul-gongora-profile")
    assert "name" in raul
    assert "artifactCount" in raul
    assert "artifactIds" in raul
    assert isinstance(raul["artifactIds"], list)
    assert len(raul["artifactIds"]) >= 1
    assert "cv-english-source" in raul["artifactIds"]
    assert raul["artifactCount"] >= 1


def test_generate_artifact_with_profile_id() -> None:
    response = client.post(
        "/generate/artifact",
        json={"profile_id": "raul-gongora-profile", "artifact_id": "cv-english-source", "output_format": "markdown"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert len(response.text) > 0


def test_generate_artifact_with_profile_id_reports_missing() -> None:
    response = client.post(
        "/generate/artifact",
        json={"profile_id": "nonexistent-profile", "artifact_id": "cv-english-source", "output_format": "markdown"},
    )

    assert response.status_code == 404
    assert "Profile not found" in response.json()["detail"]


def test_generate_markdown_cv_with_profile_id() -> None:
    response = client.post(
        "/generate/markdown-cv",
        json={"profile_id": "raul-gongora-profile", "artifact_id": "cv-english-source"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")


def test_generate_artifact_backward_compat_profile_path(tmp_path: Path) -> None:
    profile_file = tmp_path / "profile.yaml"
    profile_file.write_text(
        yaml.safe_dump(
            {
                "profileVersion": "1.0.0",
                "person": {"id": "person-1", "names": [{"value": "Jane Doe"}]},
                "skills": [{"id": "skill-1", "name": "AI workflow design"}],
                "artifacts": [
                    {
                        "id": "artifact-1",
                        "artifactType": "CV",
                        "sourceRefs": [{"id": "skill-1", "type": "skill"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    response = client.post(
        "/generate/artifact",
        json={"profile_id": "dummy", "profile_path": str(profile_file), "artifact_id": "artifact-1", "output_format": "markdown"},
    )

    assert response.status_code == 200
    assert "# Jane Doe" in response.text


def test_optimization_summary_included_in_tailored_response() -> None:
    response = client.post(
        "/generate/artifact",
        json={
            "profile_id": "raul-gongora-profile",
            "artifact_id": "cv-english-source",
            "output_format": "markdown",
            "job_description": "DevSecOps engineer with Kubernetes experience",
        },
    )

    assert response.status_code == 200
    summary_header = response.headers.get("X-Optimization-Summary")
    assert summary_header is not None
    import json
    summary = json.loads(summary_header)
    assert "total_profile_elements" in summary
    assert "included_profile_elements" in summary
    assert "profile_coverage" in summary
    assert "additional_evidence" in summary
    assert "skills_evaluated" in summary
    assert "experiences_evaluated" in summary
    assert "projects_evaluated" in summary
    assert "achievements_evaluated" in summary
    assert "certifications_evaluated" in summary
    assert "education_evaluated" in summary
    assert summary["total_profile_elements"] > 0
    assert summary["skills_evaluated"] == 6
    assert summary["experiences_evaluated"] == 6

    # Tailored CV must not leak internal implementation metadata
    for leak in ("Artifact:", "Derived from profile version", "profileVersion", "artifact_id", "artifactId"):
        assert leak not in response.text


def test_optimization_summary_included_in_interest_letter_response() -> None:
    response = client.post(
        "/generate/artifact",
        json={
            "profile_id": "raul-gongora-profile",
            "artifact_id": "artf-standard_interest_letter-person-raul-gongora",
            "output_format": "markdown",
            "job_description": "DevSecOps engineer with Kubernetes experience",
        },
    )

    assert response.status_code == 200
    status_header = response.headers.get("X-Optimization-Status")
    assert status_header is not None
    message_header = response.headers.get("X-Optimization-Message")
    assert message_header is not None
    summary_header = response.headers.get("X-Optimization-Summary")
    assert summary_header is not None
    import json
    summary = json.loads(summary_header)
    assert summary["total_profile_elements"] == 23
    assert summary["included_profile_elements"] == 13
    assert summary["profile_coverage"] == 56.5
    assert summary["additional_evidence"] == 0
    assert summary["skills_evaluated"] == 6
    assert summary["experiences_evaluated"] == 6

    # The interest letter references only 13 of 23 profile elements, but the
    # profile has no evidence model, so zero ADD recommendations is correct.
    assert status_header == "no_matches"

    # Same header contract as CV: X-Recommendations is only present when non-empty
    assert response.headers.get("X-Recommendations") is None

    # The generated document is still a proper interest letter
    assert "Interest Letter" in response.text
    assert "Dear" in response.text


def test_interest_letter_without_job_description_has_no_optimization_headers() -> None:
    response = client.post(
        "/generate/artifact",
        json={
            "profile_id": "raul-gongora-profile",
            "artifact_id": "artf-standard_interest_letter-person-raul-gongora",
            "output_format": "markdown",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("X-Optimization-Status") is None
    assert response.headers.get("X-Optimization-Summary") is None
    assert response.headers.get("X-Recommendations") is None
    assert "Interest Letter" in response.text


def test_optimization_summary_included_in_optimize_cv_response() -> None:
    response = client.post(
        "/optimize-cv",
        json={
            "profile": {
                "profileVersion": "1.0.0",
                "person": {"id": "person-1", "names": [{"value": "Jane Doe"}]},
                "skills": [{"id": "skill-1", "name": "Python"}, {"id": "skill-2", "name": "Kubernetes"}],
                "evidence": [{"id": "ev-1", "relatedRefs": [{"id": "skill-2", "type": "skill"}]}],
                "artifacts": [
                    {
                        "id": "artifact-1",
                        "artifactType": "CV",
                        "sourceRefs": [{"id": "skill-1", "type": "skill"}],
                    }
                ],
            },
            "artifact_id": "artifact-1",
            "job_description": "Python developer with Kubernetes experience",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "summary" in body
    summary = body["summary"]
    assert summary["total_profile_elements"] == 2
    assert summary["included_profile_elements"] == 1
    assert summary["profile_coverage"] == 50.0
    assert summary["additional_evidence"] == 1
    assert summary["skills_evaluated"] == 2
    assert summary["requirements_detected"] is not None
    assert summary["requirements_detected"] > 0
    assert summary["requirements_matched"] is not None
    assert summary["requirement_coverage"] is not None


def test_optimization_summary_no_job_description() -> None:
    response = client.post(
        "/generate/artifact",
        json={
            "profile_id": "raul-gongora-profile",
            "artifact_id": "cv-english-source",
            "output_format": "markdown",
        },
    )

    assert response.status_code == 200
    summary_header = response.headers.get("X-Optimization-Summary")
    assert summary_header is None


def test_optimization_summary_deterministic() -> None:
    from careeros import CVOptimizer, ProfileLoader, SchemaLoader
    from pathlib import Path as P

    REPO_ROOT = P(__file__).resolve().parents[1]
    schema_loader = SchemaLoader(REPO_ROOT / "schemas")
    profile = ProfileLoader(schema_loader).load(REPO_ROOT / "profiles" / "raul-gongora-profile.yaml")

    optimizer = CVOptimizer(profile)
    result = optimizer.optimize_cv("cv-english-source", "DevSecOps engineer with Kubernetes experience")

    s = result.summary
    assert s is not None
    assert s.total_profile_elements == 23
    assert s.included_profile_elements == 23
    assert s.profile_coverage == 100.0
    assert s.additional_evidence == 0
    assert s.skills_evaluated == 6
    assert s.experiences_evaluated == 6
    assert s.projects_evaluated == 1
    assert s.achievements_evaluated == 3
    assert s.certifications_evaluated == 6
    assert s.education_evaluated == 1
    assert s.requirements_detected is not None
    assert s.requirements_detected > 0
    assert s.requirements_matched is not None
    assert s.requirement_coverage is not None


def test_optimization_summary_multilingual_swedish_job_description() -> None:
    """Regression: an English canonical profile matched against a Swedish job description must
    still produce populated tailored-profile statistics via canonical concept matching, guarding
    the multilingual matching behavior introduced by 80698cc. Swedish-only expressions resolve
    to canonical concepts: 'informationssäkerhet'/'nätverkssäkerhet' -> Cloud Security,
    'monitorering' -> Monitoring & Observability, 'säkerhetskontroller' -> Security."""
    swedish_job_description = (
        "Vi söker en DevSecOps-ingenjör till vårt team. Du arbetar med monitorering och "
        "säkerhetsverktyg för vår molnmiljö, och du ansvarar för informationssäkerhet och "
        "nätverkssäkerhet i Azure. Vi lägger stor vikt vid säkerhetskontroller i hela "
        "leveranskedjan. Erfarenhet av Kubernetes och Docker samt CI/CD-pipelines är ett "
        "krav. Kunskaper i Python är meriterande."
    )

    response = client.post(
        "/generate/artifact",
        json={
            "profile_id": "raul-gongora-profile",
            "artifact_id": "cv-english-source",
            "output_format": "markdown",
            "job_description": swedish_job_description,
        },
    )

    assert response.status_code == 200
    summary_header = response.headers.get("X-Optimization-Summary")
    assert summary_header is not None
    import json
    summary = json.loads(summary_header)

    assert summary["profile_coverage"] is not None
    assert summary["profile_coverage"] > 0

    assert summary["requirement_coverage"] is not None
    assert summary["requirement_coverage"] > 0

    assert summary["requirements_detected"] is not None
    assert summary["requirements_detected"] > 0

    assert summary["requirements_matched"] is not None
    assert summary["requirements_matched"] > 0
    assert summary["matched_requirements"]

    assert summary["target_context_emphasis"]

    assert "Cloud Security" in summary["matched_requirements"]
    assert "Monitoring & Observability" in summary["matched_requirements"]
    assert "Security" in summary["matched_requirements"]


def test_optimizer_compute_scores_with_emphasis_no_crash() -> None:
    """Regression test: _compute_scores must not crash when profile has targetContext emphasis
    and unreferenced elements exist. Verifies fix for optimizer.py element_text NameError."""
    from careeros import CVOptimizer

    profile = {
        "profileVersion": "1.0.0",
        "person": {"id": "p1", "names": [{"value": "Test User", "usage": "professional"}]},
        "targetContexts": [
            {
                "id": "tc1",
                "label": "Test context",
                "emphasis": ["DevSecOps", "Cloud", "Kubernetes"],
            }
        ],
        "skills": [
            {"id": "s1", "name": "Python", "evidenceRefs": [{"id": "ev1", "type": "evidence"}]},
            {"id": "s2", "name": "Kubernetes", "evidenceRefs": [{"id": "ev2", "type": "evidence"}]},
        ],
        "evidence": [
            {"id": "ev1", "title": "Built Python tools"},
            {"id": "ev2", "title": "Managed K8s clusters"},
        ],
        "artifacts": [
            {
                "id": "cv1",
                "title": "Test CV",
                "artifactType": "CV",
                "sourceRefs": [{"id": "s1", "type": "skill"}],
            }
        ],
    }

    optimizer = CVOptimizer(profile)
    result = optimizer.optimize_cv("cv1", "DevSecOps engineer with Kubernetes experience")

    assert result.status in ("recommendations_available", "no_matches")
    if result.recommendations:
        rec = result.recommendations[0]
        assert rec.display_name
        assert rec.scores.get("target_context_match", 0) >= 0


def test_recommendation_serialization_contains_displayName() -> None:
    """Regression test: Recommendation.to_dict() must include both display_name and displayName
    so the frontend can read recommendation titles regardless of naming convention."""
    from careeros import Recommendation

    rec = Recommendation(
        id="rec-1",
        type="skill",
        operation="ADD",
        display_name="Kubernetes",
        details={},
        evidence=[],
        scores={"weighted_total": 2.5},
    )

    result = rec.to_dict()
    assert "display_name" in result
    assert result["display_name"] == "Kubernetes"
    assert "displayName" in result
    assert result["displayName"] == "Kubernetes"


def test_duplicate_narrative_suppressed_for_rene_profile_regression(tmp_path: Path) -> None:
    """Regression (M1.25 → suppression): a repeated experience scope (synthetic
    Rene Hechavarria persona) is suppressed deterministically on the tailored CV
    contract only, without altering the canonical profile file.
    """
    from careeros import ProfileLoader, SchemaLoader, EvidenceSelector, ExportContractBuilder
    REPO_ROOT = Path(__file__).resolve().parents[1]
    repeated_scope = (
        "Familiar with the Agile way of working and DevOps concepts. "
        "Possesses first-rate communication skills which are used to forge "
        "productive relationships with stakeholders, business users and customers."
    )
    profile_path = tmp_path / "profiles" / "staging" / "person-hechavarria-profile.yaml"
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(
        yaml.safe_dump(
            {
                "profileVersion": "1.0.0",
                "person": {
                    "id": "person-hechavarria",
                    "names": [{"value": "Rene Hechavarria", "usage": "professional"}],
                },
                "professionalSummaries": [
                    {
                        "id": "sum-1",
                        "text": (
                            "A trusted Technical Consultant with broad skills in System "
                            "Administration and Implementation. "
                            f"{repeated_scope} "
                            "Passionate about delivering exceptional customer service standards."
                        ),
                    }
                ],
                "experiences": [
                    {"id": "exp-1", "title": "Consultant", "scope": repeated_scope},
                    {"id": "exp-2", "title": "Senior Consultant", "scope": repeated_scope},
                    {"id": "exp-3", "title": "Principal Consultant", "scope": repeated_scope},
                ],
                "artifacts": [
                    {
                        "id": "artf-standard_cv-person-hechavarria",
                        "title": "Standard CV",
                        "artifactType": "CV",
                        "sourceRefs": [
                            {"id": "exp-1", "type": "experience"},
                            {"id": "exp-2", "type": "experience"},
                            {"id": "exp-3", "type": "experience"},
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    profile = ProfileLoader(SchemaLoader(REPO_ROOT / "schemas")).load(profile_path)
    original_bytes = profile_path.read_bytes()

    contract = ExportContractBuilder(SchemaLoader(REPO_ROOT / "schemas")).build(
        profile, "artf-standard_cv-person-hechavarria", validate=False
    )
    # Verify the raw profile file is untouched after load/build
    assert profile_path.read_bytes() == original_bytes

    selected = EvidenceSelector().select(contract)
    # Suppression should have removed duplicate experience scopes from the
    # contract; the canonical profile file remains unchanged (verified above).
    exp_scopes = {
        s.id: s.data.get("scope")
        for s in selected.sources if s.type.lower() == "experience"
    }
    # The profile contains three experiences with identical scope text; the
    # narrative is duplicated with the professional summary, so suppression
    # clears the duplicate scopes.
    cleared_scopes = [k for k, v in exp_scopes.items() if v is None]
    assert len(cleared_scopes) >= 2, f"Expected at least 2 duplicate scopes cleared, got {cleared_scopes}"


def test_list_profiles_returns_profile_summaries() -> None:
    """GET /profiles returns list of ProfileSummary DTOs with all required fields."""
    response = client.get("/profiles")
    assert response.status_code == 200
    profiles = response.json()
    assert isinstance(profiles, list)
    if profiles:
        p = profiles[0]
        assert "id" in p
        assert "name" in p
        assert "headline" in p
        assert "artifactCount" in p
        assert "artifactIds" in p
        assert "importedAt" in p
        assert isinstance(p["artifactIds"], list)


def test_get_profile_returns_details() -> None:
    """GET /profiles/{id} returns ProfileDetails DTO with full person and artifacts."""
    response = client.get("/profiles/raul-gongora-profile")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "raul-gongora-profile"
    assert "person" in body
    assert "firstName" in body["person"]
    assert "lastName" in body["person"]
    assert "headline" in body["person"]
    assert "artifacts" in body
    assert isinstance(body["artifacts"], list)
    if body["artifacts"]:
        art = body["artifacts"][0]
        assert "id" in art
        assert "type" in art
        assert "name" in art
        assert "sourceCount" in art
    assert "summary" in body
    assert "importedAt" in body


def test_get_profile_not_found() -> None:
    """GET /profiles/{id} returns 404 for non-existent profile."""
    response = client.get("/profiles/non-existent-profile")
    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "NOT_FOUND"


def test_get_canonical_profile_returns_persisted_profile() -> None:
    """GET /profiles/{id}/canonical returns the canonical profile exactly as persisted.

    The payload must keep canonical internals (profileVersion, person.names,
    person.positioning) and must not be flattened into the presentation DTO.
    """
    response = client.get("/profiles/raul-gongora-profile/canonical")
    assert response.status_code == 200
    body = response.json()
    assert "profileVersion" in body
    person = body["person"]
    assert person["id"]
    assert isinstance(person["names"], list)
    assert "positioning" in person
    # Presentation-DTO fields must NOT leak into the canonical payload
    assert "firstName" not in person
    assert "headline" not in person


def test_get_canonical_profile_not_found() -> None:
    """GET /profiles/{id}/canonical returns 404 for non-existent profile."""
    response = client.get("/profiles/non-existent-profile/canonical")
    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "NOT_FOUND"


def test_get_profile_returns_clean_dto_no_canonical_leakage() -> None:
    """GET /profiles/{id} must not leak canonical model internals into the DTO."""
    response = client.get("/profiles/raul-gongora-profile")
    assert response.status_code == 200
    body = response.json()
    # Canonical internals that must NOT appear in the frontend DTO
    assert "names" not in body.get("person", {})
    assert "positioning" not in body.get("person", {})
    assert "sourceRefs" not in [a for a in body.get("artifacts", [])]
    assert "profileVersion" not in body
    assert "targetContexts" not in body
    # New DTO fields that expose entity collections
    assert isinstance(body.get("professionalSummaries"), list)
    assert isinstance(body.get("experiences"), list)
    assert isinstance(body.get("skills"), list)
    assert isinstance(body.get("education"), list)
    assert isinstance(body.get("certifications"), list)
    assert isinstance(body.get("projects"), list)
    # Entity DTOs should not leak canonical internal fields
    for exp in body["experiences"]:
        assert "sourceRefs" not in exp
        assert "organizationRefs" not in exp


def test_profile_summary_includes_new_fields() -> None:
    """ProfileSummary in profile list includes headline and importedAt."""
    response = client.get("/profiles")
    assert response.status_code == 200
    raul = next((p for p in response.json() if p["id"] == "raul-gongora-profile"), None)
    assert raul is not None
    assert raul["headline"] != ""
    assert "importedAt" in raul


def test_delete_profile_returns_204() -> None:
    """DELETE /profiles/{id} returns 204 for an existing profile."""
    from api.main import PROFILES_ROOT as _r
    import shutil, tempfile
    test_profile = _r / "test-delete-profile.yaml"
    try:
        test_profile.write_text(
            "profileVersion: \"1.0.0\"\n"
            "person:\n"
            "  id: p1\n"
            "  names:\n"
            "    - value: Test Delete\n"
            "person:\n"
            "  id: p1\n"
            "  names:\n"
            "    - value: Test Delete\n"
            "      usage: professional\n"
            "  positioning:\n"
            "    headline: Test\n"
        )
        response = client.delete("/profiles/test-delete-profile")
        assert response.status_code == 204
        assert not test_profile.exists()
    finally:
        if test_profile.exists():
            test_profile.unlink()


def test_delete_profile_not_found() -> None:
    """DELETE /profiles/{id} returns 404 for non-existent profile."""
    response = client.delete("/profiles/non-existent-delete-test")
    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "NOT_FOUND"


def test_import_profile_invalid_file_type() -> None:
    """POST /profiles/import returns 400 for unsupported file types."""
    response = client.post(
        "/profiles/import",
        files={"file": ("test.pdf", b"%PDF-1.4 fake pdf", "application/pdf")},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "INVALID_FILE"


def test_import_profile_file_too_large() -> None:
    """POST /profiles/import returns 400 for files exceeding the size limit."""
    large_content = b"x" * (11 * 1024 * 1024)
    response = client.post(
        "/profiles/import",
        files={"file": ("large.docx", large_content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "FILE_TOO_LARGE"


def test_import_profile_duplicate_returns_409(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """POST /profiles/import maps a DuplicateProfileError to HTTP 409 JSON."""
    from careeros.exceptions import DuplicateProfileError
    import api.main as api_main

    class _StubDuplicatePipeline:
        def run(self, source_path, output_path=None, schema=None, source_metadata=None):
            raise DuplicateProfileError(
                "person-dup", "profiles/staging/person-dup-profile.yaml"
            )

    monkeypatch.setattr(api_main, "AcquisitionPipeline", _StubDuplicatePipeline)

    existing = tmp_path / "person-dup-profile.yaml"
    existing.write_text("keep: me\n", encoding="utf-8")

    for _ in range(2):
        response = client.post(
            "/profiles/import",
            files={"file": ("resume.docx", b"x", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        assert response.status_code == 409
        body = response.json()
        assert body["error"] == "DUPLICATE_PROFILE"
        assert "person-dup" in body["detail"]
        assert isinstance(body["detail"], str)

    assert existing.read_text(encoding="utf-8") == "keep: me\n"


_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class _StubImportPipeline:
    """Mimics AcquisitionPipeline.run for Phase 2A API tests.

    Writes the configured profile payload into the (monkeypatched) staging
    directory and returns its path, mirroring the real pipeline's provenance
    fields so the API read-back and classification behave realistically.
    """

    def __init__(self, person: dict, source_hash: str = "") -> None:
        self.person = person
        self.source_hash = source_hash

    def run(self, source_path, output_path=None, schema=None, source_metadata=None):
        import api.main as api_main
        from careeros.exceptions import DuplicateProfileError

        meta = source_metadata or {}
        data = {
            "profileVersion": "1.0.0",
            "person": self.person,
            "professionalSummaries": [],
            "experiences": [],
            "organizations": [],
            "projects": [],
            "skills": [],
            "achievements": [],
            "evidence": [],
            "education": [],
            "certifications": [],
            "artifacts": [],
            "targetContexts": [],
            "extensions": {
                "_acquisition": {
                    "sourceName": meta.get("sourceName", ""),
                    "sourceHash": self.source_hash or meta.get("sourceHash", ""),
                    "sourceDocument": str(source_path),
                    "extractionTimestamp": "2026-01-01T00:00:00+00:00",
                    "importedAt": "2026-01-01T00:00:00+00:00",
                },
                "importedAt": "2026-01-01T00:00:00+00:00",
            },
        }
        person_id = self.person["id"]
        staging = api_main.PROFILES_ROOT / "staging"
        staging.mkdir(parents=True, exist_ok=True)
        path = staging / f"{person_id}-profile.yaml"
        if path.is_file():
            raise DuplicateProfileError(person_id, str(path))
        path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
        return path


@pytest.fixture
def isolated_profile_store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Redirect the API profile store to a temporary directory."""
    import api.main as api_main
    from careeros.profile_repository import ProfileRepository

    root = tmp_path / "profiles"
    root.mkdir()
    monkeypatch.setattr(api_main, "PROFILES_ROOT", root)
    monkeypatch.setattr(api_main, "PROFILE_REPOSITORY", ProfileRepository(root))
    return root


def _person(pid: str, name: str | None = None, email: str | None = None) -> dict:
    person: dict = {"id": pid}
    if name:
        person["names"] = [{"value": name, "usage": "professional"}]
    if email:
        person["contact"] = {"email": email}
    return person


def _write_profile(rel_path: Path, person: dict, *, source_hash: str | None = None) -> Path:
    import api.main as api_main

    data = {
        "profileVersion": "1.0.0",
        "person": person,
        "professionalSummaries": [],
        "experiences": [],
        "organizations": [],
        "projects": [],
        "skills": [],
        "achievements": [],
        "evidence": [],
        "education": [],
        "certifications": [],
        "artifacts": [],
        "targetContexts": [],
        "extensions": {},
    }
    if source_hash:
        data["extensions"]["_acquisition"] = {"sourceHash": source_hash}
    path = api_main.PROFILES_ROOT / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def test_import_retains_source_and_records_provenance(
    isolated_profile_store: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Phase 2A: upload is hashed, the source is retained, provenance is recorded."""
    import hashlib

    import api.main as api_main

    payload = b"phase-2a-retention-docx-bytes"
    source_hash = hashlib.sha256(payload).hexdigest()
    stub = _StubImportPipeline(_person("person-anna-lindqvist", name="Anna Lindqvist"))
    monkeypatch.setattr(api_main, "AcquisitionPipeline", lambda: stub)

    response = client.post(
        "/profiles/import",
        files={"file": ("anna-cv.docx", payload, _DOCX_MIME)},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["profileId"] == "person-anna-lindqvist-profile"
    assert body["classification"]["result"] == "NEW_PERSON"

    retained = isolated_profile_store / "staging" / "_sources" / f"{source_hash}.docx"
    assert retained.read_bytes() == payload

    profile_data = yaml.safe_load(
        (isolated_profile_store / "staging" / "person-anna-lindqvist-profile.yaml").read_text(
            encoding="utf-8"
        )
    )
    acquisition = profile_data["extensions"]["_acquisition"]
    assert acquisition["sourceName"] == "anna-cv.docx"
    assert acquisition["sourceHash"] == source_hash
    assert acquisition["importedAt"]
    assert profile_data["extensions"]["importedAt"] == acquisition["importedAt"]
    assert body["profile"]["importedAt"] == acquisition["importedAt"]

    # the retained source store must never be discovered as a profile
    listed = [p["id"] for p in client.get("/profiles").json()]
    assert listed == ["person-anna-lindqvist-profile"]


def test_import_same_document_detected(
    isolated_profile_store: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Phase 2A: a byte-identical re-import is classified SAME_DOCUMENT."""
    import hashlib

    import api.main as api_main

    payload = b"same-document-bytes"
    source_hash = hashlib.sha256(payload).hexdigest()
    _write_profile(
        Path("staging") / "person-jane-doe-profile.yaml",
        _person("person-jane-doe", name="Jane Doe"),
        source_hash=source_hash,
    )
    stub = _StubImportPipeline(
        _person("person-raul-gongora-betancourt", name="Raul Gongora Betancourt")
    )
    monkeypatch.setattr(api_main, "AcquisitionPipeline", lambda: stub)

    response = client.post(
        "/profiles/import",
        files={"file": ("resume.docx", payload, _DOCX_MIME)},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["classification"]["result"] == "SAME_DOCUMENT"
    assert body["classification"]["candidates"][0]["profileId"] == "person-jane-doe-profile"
    assert body["classification"]["candidates"][0]["matchedOn"] == ["sourceHash"]


def test_import_possible_same_person_without_merge_or_promotion(
    isolated_profile_store: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Phase 2A: different deterministic ids for the same human surface a candidate
    without merging or promoting, and leave the canonical profile untouched."""
    import api.main as api_main

    canonical = _write_profile(
        Path("raul-gongora-profile.yaml"),
        _person("person-raul-gongora", name="Raul Gongora"),
    )
    before = canonical.read_bytes()
    stub = _StubImportPipeline(
        _person("person-raul-gongora-betancourt", name="Raul Gongora Betancourt")
    )
    monkeypatch.setattr(api_main, "AcquisitionPipeline", lambda: stub)

    response = client.post(
        "/profiles/import",
        files={"file": ("new-cv.docx", b"new-cv-bytes", _DOCX_MIME)},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["classification"]["result"] == "POSSIBLE_SAME_PERSON"
    candidate = body["classification"]["candidates"][0]
    assert candidate["profileId"] == "raul-gongora-profile"
    assert "name-tokens" in candidate["matchedOn"]

    # no merge, no promotion: canonical untouched, import stays in staging
    assert canonical.read_bytes() == before
    assert (
        isolated_profile_store / "staging" / "person-raul-gongora-betancourt-profile.yaml"
    ).exists()


def test_import_identity_conflict_reported_not_merged(
    isolated_profile_store: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Phase 2A: same name with a different email is a conflict, never a merge."""
    import api.main as api_main

    _write_profile(
        Path("staging") / "person-gongora-profile.yaml",
        _person("person-gongora", name="Raul Gongora Betancourt", email="old@example.com"),
    )
    stub = _StubImportPipeline(
        _person(
            "person-raul-gongora-betancourt",
            name="Raul Gongora Betancourt",
            email="new@example.com",
        )
    )
    monkeypatch.setattr(api_main, "AcquisitionPipeline", lambda: stub)

    response = client.post(
        "/profiles/import",
        files={"file": ("cv.docx", b"conflict-bytes", _DOCX_MIME)},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["classification"]["result"] == "IDENTITY_CONFLICT"
    candidate = body["classification"]["candidates"][0]
    assert candidate["conflictingOn"] == ["email"]


def test_dto_mapping_profile_summary() -> None:
    """Verify DTO mapping layer produces correct ProfileSummary from canonical data."""
    from api.dto import to_profile_summary

    canonical = {
        "profileVersion": "1.0.0",
        "person": {
            "id": "p1",
            "names": [{"value": "Jane Doe", "usage": "professional"}],
            "positioning": {"headline": "Software Engineer"},
        },
        "artifacts": [
            {"id": "cv1", "artifactType": "CV", "title": "Test CV"},
        ],
        "extensions": {"importedAt": "2026-01-01T00:00:00Z"},
    }

    result = to_profile_summary(canonical, "jane-doe")
    assert result["id"] == "jane-doe"
    assert result["name"] == "Jane Doe"
    assert result["headline"] == "Software Engineer"
    assert result["artifactCount"] == 1
    assert result["artifactIds"] == ["cv1"]
    assert result["importedAt"] == "2026-01-01T00:00:00Z"


def test_dto_mapping_profile_details() -> None:
    """Verify DTO mapping layer produces correct ProfileDetails from canonical data."""
    from api.dto import to_profile_details

    canonical = {
        "profileVersion": "1.0.0",
        "person": {
            "id": "p1",
            "names": [{"value": "Jane Doe", "usage": "professional"}],
            "positioning": {"headline": "Software Engineer"},
            "location": {"city": "Stockholm", "country": "Sweden"},
            "languages": [{"name": "English", "proficiency": "fluent"}],
        },
        "professionalSummaries": [{"id": "s1", "text": "Experienced engineer."}],
        "artifacts": [
            {
                "id": "cv1",
                "artifactType": "CV",
                "title": "Test CV",
                "sourceRefs": [{"id": "s1", "type": "skill"}],
            }
        ],
        "extensions": {"importedAt": "2026-01-01T00:00:00Z"},
    }

    result = to_profile_details(canonical, "jane-doe")
    assert result["id"] == "jane-doe"
    assert result["person"]["firstName"] == "Jane"
    assert result["person"]["lastName"] == "Doe"
    assert result["person"]["headline"] == "Software Engineer"
    assert result["person"]["city"] == "Stockholm"
    assert result["person"]["country"] == "Sweden"
    assert len(result["person"]["languages"]) == 1
    assert result["artifacts"][0]["type"] == "CV"
    assert result["artifacts"][0]["sourceCount"] == 1
    assert result["summary"] == "Experienced engineer."
    assert result["importedAt"] == "2026-01-01T00:00:00Z"


def test_dto_mapping_import_response() -> None:
    """Verify DTO mapping layer produces correct ImportResponse."""
    from api.dto import to_import_response

    canonical = {
        "profileVersion": "1.0.0",
        "person": {
            "id": "p1",
            "names": [{"value": "Jane Doe", "usage": "professional"}],
            "positioning": {"headline": "Software Engineer"},
        },
        "artifacts": [],
        "extensions": {"importedAt": "2026-01-01T00:00:00Z"},
    }

    result = to_import_response(canonical, "jane-doe")
    assert result["profileId"] == "jane-doe"
    assert result["profile"]["id"] == "jane-doe"
    assert result["profile"]["name"] == "Jane Doe"
    assert result["profile"]["headline"] == "Software Engineer"


def test_dto_mapping_missing_fields() -> None:
    """DTO mapping handles missing optional fields gracefully."""
    from api.dto import to_profile_summary, to_profile_details

    minimal = {
        "profileVersion": "1.0.0",
        "person": {"id": "p1", "names": []},
        "artifacts": [],
    }

    summary = to_profile_summary(minimal, "empty-profile")
    assert summary["name"] == ""
    assert summary["headline"] == ""
    assert summary["artifactCount"] == 0
    assert summary["artifactIds"] == []
    assert summary["importedAt"] == ""

    details = to_profile_details(minimal, "empty-profile")
    assert details["person"]["firstName"] == ""
    assert details["person"]["lastName"] == ""
    assert details["person"]["headline"] == ""
    assert details["person"]["city"] is None
    assert details["person"]["country"] is None
    assert details["summary"] is None
    assert details["artifacts"] == []


ANALYZE_TEST_PROFILE = {
    "profileVersion": "1.0.0",
    "person": {"id": "analyze-test-profile", "names": [{"value": "Test User", "usage": "professional"}], "positioning": {"headline": "Engineer"}},
    "experiences": [{"id": "exp-1", "title": "Engineer", "organizationRefs": [{"id": "org-1", "type": "organization"}], "dateRange": {"start": "2020-01", "end": "2023-12"}}],
    "skills": [{"id": "skill-1", "name": "Python"}],
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


@pytest.fixture
def analyze_profile() -> str:
    """Create a clean test profile for analyze tests and return its ID."""
    import yaml
    from api.main import PROFILES_ROOT

    profile_id = "analyze-test-profile"
    profile_path = PROFILES_ROOT / f"{profile_id}.yaml"
    profile_path.write_text(yaml.safe_dump(ANALYZE_TEST_PROFILE), encoding="utf-8")
    yield profile_id
    if profile_path.exists():
        profile_path.unlink()


def test_analyze_profile_returns_reasoning_report(analyze_profile: str) -> None:
    """POST /analyze returns a complete ReasoningReport for an existing profile."""
    response = client.post("/analyze", json={"profileId": analyze_profile})
    assert response.status_code == 200
    body = response.json()
    assert body["engine_version"] == "1.0.0"
    assert "generated_at" in body
    assert body["profile_id"] == analyze_profile
    assert "findings" in body
    assert isinstance(body["findings"], list)
    assert "findings_by_type" in body
    assert "summary" in body
    assert body["summary"]["total_findings"] > 0
    assert body["summary"]["total_rules_executed"] > 0
    assert "execution_stats" in body


def test_analyze_profile_exposes_recommendations(analyze_profile: str) -> None:
    """POST /analyze returns deterministic profile recommendations."""
    response = client.post("/analyze", json={"profileId": analyze_profile})
    assert response.status_code == 200
    body = response.json()
    assert "recommendations" in body
    assert isinstance(body["recommendations"], list)
    assert len(body["recommendations"]) >= 1
    for rec in body["recommendations"]:
        assert rec["id"]
        assert rec["title"]
        assert rec["reason"]
        assert rec["explanation"]
        assert rec["suggested_action"]
        assert isinstance(rec["examples"], list) and rec["examples"]
        assert rec["priority"] in ("high", "medium", "low")
        assert rec["estimated_impact"] in ("high", "medium", "low")
        assert rec["detected_pattern"]
        assert isinstance(rec["missing_information"], list) and rec["missing_information"]
        assert rec["recruiter_impact"]
        assert rec["triggered_rule"]
        assert rec["confidence"] in ("high", "medium", "low")
        assert "future_evidence" in rec


def test_analyze_profile_not_found() -> None:
    """POST /analyze returns 404 for non-existent profile."""
    response = client.post("/analyze", json={"profileId": "non-existent-profile"})
    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "NOT_FOUND"


def test_analyze_profile_finding_structure(analyze_profile: str) -> None:
    """Each finding in the report has the required fields."""
    response = client.post("/analyze", json={"profileId": analyze_profile})
    assert response.status_code == 200
    body = response.json()
    for f in body["findings"]:
        assert "rule_id" in f
        assert "finding_type" in f
        assert "value" in f
        assert "confidence" in f
        assert isinstance(f["confidence"], float)
        assert 0.0 <= f["confidence"] <= 1.0


def test_analyze_profile_summary_fields(analyze_profile: str) -> None:
    """The report summary includes all expected fields."""
    response = client.post("/analyze", json={"profileId": analyze_profile})
    assert response.status_code == 200
    s = response.json()["summary"]
    assert "total_findings" in s
    assert "findings_by_type_count" in s
    assert "total_rules_executed" in s
    assert "confidence_distribution" in s
    assert "execution_time_seconds" in s
    assert s["execution_time_seconds"] >= 0


def test_analyze_profile_execution_stats(analyze_profile: str) -> None:
    """Execution stats contain rule-level detail."""
    response = client.post("/analyze", json={"profileId": analyze_profile})
    assert response.status_code == 200
    stats = response.json()["execution_stats"]
    assert "total_rules" in stats
    assert "total_findings" in stats
    assert "execution_time_seconds" in stats
    assert "rules_executed" in stats
    assert isinstance(stats["rules_executed"], list)
    assert "findings_per_rule" in stats


def test_analyze_profile_with_empty_profile() -> None:
    """POST /analyze handles an empty/minimal profile gracefully."""
    import yaml
    from api.main import PROFILES_ROOT

    minimal = {
        "profileVersion": "1.0.0",
        "person": {"id": "minimal-test-profile"},
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
    profile_path = PROFILES_ROOT / "minimal-test-profile.yaml"
    try:
        profile_path.write_text(yaml.safe_dump(minimal), encoding="utf-8")
        response = client.post("/analyze", json={"profileId": "minimal-test-profile"})
        assert response.status_code == 200
        body = response.json()
        assert body["profile_id"] == "minimal-test-profile"
        assert isinstance(body["findings"], list)
        assert "summary" in body
    finally:
        if profile_path.exists():
            profile_path.unlink()


def test_analyze_profile_deterministic(analyze_profile: str) -> None:
    """Running analyze twice on the same profile yields identical findings and summary."""
    response1 = client.post("/analyze", json={"profileId": analyze_profile})
    response2 = client.post("/analyze", json={"profileId": analyze_profile})
    assert response1.status_code == 200
    assert response2.status_code == 200
    body1 = response1.json()
    body2 = response2.json()
    assert body1["findings"] == body2["findings"]
    assert body1["findings_by_type"] == body2["findings_by_type"]
    assert body1["summary"]["total_findings"] == body2["summary"]["total_findings"]
    assert body1["summary"]["total_rules_executed"] == body2["summary"]["total_rules_executed"]
    assert body1["summary"]["findings_by_type_count"] == body2["summary"]["findings_by_type_count"]
    assert body1["summary"]["confidence_distribution"] == body2["summary"]["confidence_distribution"]


def test_analyze_profile_with_parameters(analyze_profile: str) -> None:
    """POST /analyze accepts optional parameters dictionary."""
    response = client.post("/analyze", json={"profileId": analyze_profile, "parameters": {"focus": "skills"}})
    assert response.status_code == 200
    body = response.json()
    assert body["profile_id"] == analyze_profile


def test_optimizer_runs_once_per_artifact_request() -> None:
    """Regression test: /generate/artifact must not invoke the optimizer twice.
    When job_description is provided, the endpoint uses the optimization result
    returned by generate_artifact() instead of calling optimize_cv again."""
    response = client.post(
        "/generate/artifact",
        json={
            "profile_id": "raul-gongora-profile",
            "artifact_id": "cv-english-source",
            "output_format": "markdown",
            "job_description": "DevSecOps engineer with Kubernetes experience",
        },
    )

    assert response.status_code == 200
    summary_header = response.headers.get("X-Optimization-Summary")
    assert summary_header is not None, "Optimization summary header must be present when job_description is provided"

    import json
    summary = json.loads(summary_header)
    assert summary["total_profile_elements"] > 0
    assert summary["included_profile_elements"] > 0

    recommendations_header = response.headers.get("X-Recommendations")
    if recommendations_header:
        recs = json.loads(recommendations_header)
        if recs:
            rec = recs[0]
            assert "display_name" in rec
            assert "displayName" in rec
            assert rec["displayName"] == rec["display_name"]


def test_artifact_templates_endpoint() -> None:
    """GET /artifact-templates returns both registered templates."""
    response = client.get("/artifact-templates")
    assert response.status_code == 200
    templates = response.json()
    assert isinstance(templates, list)
    assert len(templates) >= 2

    cv = next((t for t in templates if t["artifactType"] == "CV"), None)
    assert cv is not None
    assert cv["id"] == "standard_cv"
    assert cv["displayName"] == "Tailored CV"

    interest = next((t for t in templates if t["artifactType"] == "INTEREST_LETTER"), None)
    assert interest is not None
    assert interest["id"] == "standard_interest_letter"
    assert interest["displayName"] == "Interest Letter"


PREVIEW_TEST_PROFILE = {
    "profileVersion": "1.0.0",
    "person": {
        "id": "preview-person",
        "names": [{"value": "Preview Person", "usage": "professional"}],
        "positioning": {"headline": "AI Platform Engineer"},
    },
    "professionalSummaries": [
        {"id": "sum-1", "label": "Summary", "text": "Deterministic preview engineer."},
    ],
    "skills": [
        {"id": "skill-1", "name": "Python"},
        {"id": "skill-2", "name": "Kubernetes"},
    ],
    "experiences": [
        {
            "id": "exp-1",
            "title": "Platform Engineer",
            "organizationRefs": [{"id": "org-1", "type": "organization"}],
            "dateRange": {"start": "2021-01", "end": "2024-12"},
            "scope": "Built deterministic preview pipelines.",
        },
    ],
    "organizations": [{"id": "org-1", "name": "ACME"}],
    "projects": [],
    "education": [],
    "certifications": [],
    "achievements": [],
    "artifacts": [],
    "targetContexts": [],
}


@pytest.fixture
def preview_profile() -> str:
    """Create a clean test profile for template preview tests and return its ID."""
    import yaml
    from api.main import PROFILES_ROOT

    profile_id = "preview-test-profile"
    profile_path = PROFILES_ROOT / f"{profile_id}.yaml"
    profile_path.write_text(yaml.safe_dump(PREVIEW_TEST_PROFILE), encoding="utf-8")
    yield profile_id
    if profile_path.exists():
        profile_path.unlink()


def _read_raw_profile(profile_id: str) -> str:
    from api.main import PROFILES_ROOT
    return (PROFILES_ROOT / f"{profile_id}.yaml").read_text(encoding="utf-8")


def test_artifact_template_preview_returns_markdown_and_source_count(preview_profile: str) -> None:
    """POST /artifact-templates/{id}/preview renders markdown with source_count."""
    response = client.post(
        "/artifact-templates/standard_cv/preview",
        json={"profile_id": preview_profile},
    )
    assert response.status_code == 200
    body = response.json()
    assert "# Preview Person" in body["markdown"]
    assert "Python" in body["markdown"]
    assert body["source_count"] == 4  # summary + 2 skills + experience
    assert isinstance(body["estimated_health_score"], int)


def test_artifact_template_preview_is_deterministic(preview_profile: str) -> None:
    """Same profile + same template produces identical preview output."""
    first = client.post(
        "/artifact-templates/standard_cv/preview",
        json={"profile_id": preview_profile},
    )
    second = client.post(
        "/artifact-templates/standard_cv/preview",
        json={"profile_id": preview_profile},
    )
    assert first.status_code == 200
    assert first.json() == second.json()


def test_artifact_template_preview_has_no_side_effects(preview_profile: str) -> None:
    """Preview is render-only: no artifact, no profile mutation, no versions."""
    import yaml
    from api.main import PROFILES_ROOT

    before = _read_raw_profile(preview_profile)
    response = client.post(
        "/artifact-templates/standard_cv/preview",
        json={"profile_id": preview_profile},
    )
    assert response.status_code == 200
    assert _read_raw_profile(preview_profile) == before

    data = yaml.safe_load(_read_raw_profile(preview_profile))
    assert data.get("artifacts") == []
    assert data.get("extensions", {}).get("_versions") is None


def test_artifact_template_preview_rejects_unknown_template(preview_profile: str) -> None:
    """Preview rejects unknown template identifiers with INVALID_TEMPLATE."""
    response = client.post(
        "/artifact-templates/not-a-template/preview",
        json={"profile_id": preview_profile},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "INVALID_TEMPLATE"


def test_artifact_template_preview_reports_missing_profile() -> None:
    """Preview reports unknown profiles with NOT_FOUND."""
    response = client.post(
        "/artifact-templates/standard_cv/preview",
        json={"profile_id": "does-not-exist"},
    )
    assert response.status_code == 404
    assert response.json()["error"] == "NOT_FOUND"


def test_artifact_template_preview_interest_letter(preview_profile: str) -> None:
    """Interest letter template renders a markdown preview through the pipeline."""
    response = client.post(
        "/artifact-templates/standard_interest_letter/preview",
        json={"profile_id": preview_profile},
    )
    assert response.status_code == 200
    body = response.json()
    assert "Preview Person" in body["markdown"]
    assert "Python" in body["markdown"]
    assert body["source_count"] == 4  # summary + experience + 2 skills


def test_standard_cv_template_preview_returns_markdown() -> None:
    """ArtifactTemplate.preview(profile) renders markdown directly from a dict."""
    from careeros.artifact_templates import StandardCVTemplate

    markdown = StandardCVTemplate().preview(PREVIEW_TEST_PROFILE)
    assert isinstance(markdown, str)
    assert "# Preview Person" in markdown
    assert "Python" in markdown


RESOLVE_TEST_PROFILE = {
    "profileVersion": "1.0.0",
    "person": {"id": "resolve-test-person", "names": [{"value": "Resolve Test", "usage": "professional"}]},
    "organizations": [{"id": "org-1", "name": "Corp"}],
    "experiences": [
        {
            "id": "exp-no-tech",
            "title": "Operations Coordinator",
            "organizationRefs": [{"id": "org-1", "type": "organization"}],
            "dateRange": {"start": "2020-01", "end": "2023-12"},
            "scope": "Coordinated operations across several departments.",
        },
    ],
    "skills": [
        {"id": "skill-python", "name": "Python"},
        {"id": "skill-observability", "name": "Observability Patterns"},
    ],
    "projects": [
        {"id": "proj-lonely", "name": "Lonely Project", "description": "A project with no links."},
    ],
    "education": [],
    "professionalSummaries": [],
    "achievements": [],
    "evidence": [],
    "certifications": [],
    "artifacts": [],
    "targetContexts": [],
}


@pytest.fixture
def resolve_profile() -> str:
    """Create a clean test profile for guided resolution tests and return its ID."""
    import yaml
    from api.main import PROFILES_ROOT

    profile_id = "resolve-test-profile"
    profile_path = PROFILES_ROOT / f"{profile_id}.yaml"
    profile_path.write_text(yaml.safe_dump(RESOLVE_TEST_PROFILE), encoding="utf-8")
    yield profile_id
    if profile_path.exists():
        profile_path.unlink()


def _read_canonical(profile_id: str) -> dict:
    import yaml
    from api.main import PROFILES_ROOT
    return yaml.safe_load((PROFILES_ROOT / f"{profile_id}.yaml").read_text(encoding="utf-8"))


def test_technologies_endpoint() -> None:
    """GET /technologies exposes the recognized technology keywords."""
    response = client.get("/technologies")
    assert response.status_code == 200
    keywords = response.json()["keywords"]
    assert isinstance(keywords, list)
    assert len(keywords) >= 50
    assert len(keywords) == len(set(keywords))
    assert keywords == sorted(keywords)
    for expected in ("python", "docker", "kubernetes", "terraform", "sql", "aws"):
        assert expected in keywords


def test_resolve_recommendation_unsupported_rule(resolve_profile: str) -> None:
    """Resolution rejects rule types outside the M1.7/M1.24 scope."""
    response = client.post(
        f"/profiles/{resolve_profile}/resolve",
        json={"triggeredRule": "UnknownRule", "elementId": "exp-no-tech"},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "UNSUPPORTED_RULE"


def test_resolve_professional_summary_creates_when_missing(resolve_profile: str) -> None:
    """Resolving a missing professional summary writes a canonical summary and clears the recommendation."""
    response = client.post(
        f"/profiles/{resolve_profile}/resolve",
        json={"triggeredRule": "GenericSummaryRule", "elementId": "", "summaryText": "Senior engineer with 8 years of experience focused on cloud reliability."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["summary"] == "Senior engineer with 8 years of experience focused on cloud reliability."

    canonical = _read_canonical(resolve_profile)
    summaries = canonical["professionalSummaries"]
    assert len(summaries) == 1
    assert summaries[0]["text"] == "Senior engineer with 8 years of experience focused on cloud reliability."
    assert summaries[0]["id"] == "professional-summary"

    analysis = client.post("/analyze", json={"profileId": resolve_profile})
    recs = analysis.json()["recommendations"]
    assert not any(
        r["triggered_rule"] == "GenericSummaryRule" for r in recs
    )


def test_resolve_professional_summary_updates_existing_and_marks_artifact_stale(resolve_profile: str) -> None:
    """Resolving an existing summary rewrites its text and marks exporting artifacts stale."""
    import yaml
    from api.main import PROFILES_ROOT

    path = PROFILES_ROOT / f"{resolve_profile}.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["professionalSummaries"] = [
        {"id": "summary-main", "label": "Professional profile", "text": "Old summary text."}
    ]
    data["artifacts"] = [
        {
            "id": "art-cv",
            "title": "Test CV",
            "artifactType": "CV",
            "sourceRefs": [{"id": "summary-main", "type": "professional_summary"}],
            "status": "current",
        }
    ]
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    response = client.post(
        f"/profiles/{resolve_profile}/resolve",
        json={"triggeredRule": "GenericSummaryRule", "elementId": "", "summaryText": "Results-driven engineer with 8 years of cloud and DevOps experience."},
    )
    assert response.status_code == 200

    canonical = _read_canonical(resolve_profile)
    assert canonical["professionalSummaries"][0]["id"] == "summary-main"
    assert canonical["professionalSummaries"][0]["label"] == "Professional profile"
    assert canonical["professionalSummaries"][0]["text"] == "Results-driven engineer with 8 years of cloud and DevOps experience."
    assert canonical["artifacts"][0]["status"] == "stale"


def test_resolve_professional_summary_requires_text(resolve_profile: str) -> None:
    """Resolution rejects an empty professional summary text."""
    response = client.post(
        f"/profiles/{resolve_profile}/resolve",
        json={"triggeredRule": "GenericSummaryRule", "elementId": "", "summaryText": "   "},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "EMPTY_SUMMARY"


def test_resolve_recommendation_profile_not_found() -> None:
    """Resolution returns 404 for a non-existent profile."""
    response = client.post(
        "/profiles/non-existent-profile/resolve",
        json={"triggeredRule": "ProjectWithoutSkillsRule", "elementId": "proj-1"},
    )
    assert response.status_code == 404
    assert response.json()["error"] == "NOT_FOUND"


def test_resolve_recommendation_element_not_found(resolve_profile: str) -> None:
    """Resolution returns 404 when the target element does not exist."""
    response = client.post(
        f"/profiles/{resolve_profile}/resolve",
        json={"triggeredRule": "ProjectWithoutSkillsRule", "elementId": "proj-missing", "skillIds": ["skill-python"]},
    )
    assert response.status_code == 404


def test_resolve_project_with_skills_and_experience(resolve_profile: str) -> None:
    """Resolving a project writes canonical skillRefs/experienceRefs and clears the recommendation."""
    response = client.post(
        f"/profiles/{resolve_profile}/resolve",
        json={
            "triggeredRule": "ProjectWithoutSkillsRule",
            "elementId": "proj-lonely",
            "skillIds": ["skill-python"],
            "experienceIds": ["exp-no-tech"],
            "technologies": [],
        },
    )
    assert response.status_code == 200
    body = response.json()
    project = next(p for p in body["profile"]["projects"] if p["id"] == "proj-lonely")
    assert project["name"] == "Lonely Project"

    canonical = _read_canonical(resolve_profile)
    proj = next(p for p in canonical["projects"] if p["id"] == "proj-lonely")
    assert proj["skillRefs"] == [{"id": "skill-python", "type": "skill"}]
    assert proj["experienceRefs"] == [{"id": "exp-no-tech", "type": "experience"}]

    analysis = client.post("/analyze", json={"profileId": resolve_profile})
    recs = analysis.json()["recommendations"]
    assert not any(
        r["element_id"] == "proj-lonely" and r["triggered_rule"] == "ProjectWithoutSkillsRule"
        for r in recs
    )


def test_resolve_experience_technologies(resolve_profile: str) -> None:
    """Resolving technologies appends recognized keywords to the experience scope and clears the recommendation."""
    response = client.post(
        f"/profiles/{resolve_profile}/resolve",
        json={
            "triggeredRule": "ExperienceNoTechnologiesRule",
            "elementId": "exp-no-tech",
            "skillIds": ["skill-python"],
            "experienceIds": [],
            "technologies": ["Terraform"],
        },
    )
    assert response.status_code == 200

    canonical = _read_canonical(resolve_profile)
    exp = next(e for e in canonical["experiences"] if e["id"] == "exp-no-tech")
    assert "Key technologies" in exp["scope"]
    assert "Python" in exp["scope"]
    assert "Terraform" in exp["scope"]

    analysis = client.post("/analyze", json={"profileId": resolve_profile})
    recs = analysis.json()["recommendations"]
    assert not any(
        r["element_id"] == "exp-no-tech" and r["triggered_rule"] == "ExperienceNoTechnologiesRule"
        for r in recs
    )


def test_resolve_skill_with_experience_evidence(resolve_profile: str) -> None:
    """Resolving a skill links experience evidence and clears the recommendation."""
    response = client.post(
        f"/profiles/{resolve_profile}/resolve",
        json={
            "triggeredRule": "SkillWithoutExperienceRule",
            "elementId": "skill-observability",
            "skillIds": [],
            "experienceIds": ["exp-no-tech"],
            "technologies": [],
        },
    )
    assert response.status_code == 200

    canonical = _read_canonical(resolve_profile)
    skill = next(s for s in canonical["skills"] if s["id"] == "skill-observability")
    assert skill["extensions"]["experienceEvidence"] == [
        {"experienceId": "exp-no-tech", "type": "experience"}
    ]

    analysis = client.post("/analyze", json={"profileId": resolve_profile})
    recs = analysis.json()["recommendations"]
    assert not any(
        r["element_id"] == "skill-observability" and r["triggered_rule"] == "SkillWithoutExperienceRule"
        for r in recs
    )


def test_resolve_skill_evidence_is_idempotent(resolve_profile: str) -> None:
    """Repeated skill resolution does not duplicate experience evidence entries."""
    payload = {
        "triggeredRule": "SkillWithoutExperienceRule",
        "elementId": "skill-observability",
        "skillIds": [],
        "experienceIds": ["exp-no-tech", "exp-no-tech"],
        "technologies": [],
    }
    first = client.post(f"/profiles/{resolve_profile}/resolve", json=payload)
    second = client.post(f"/profiles/{resolve_profile}/resolve", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200

    canonical = _read_canonical(resolve_profile)
    skill = next(s for s in canonical["skills"] if s["id"] == "skill-observability")
    assert len(skill["extensions"]["experienceEvidence"]) == 1


def _has_measurable_achievement_rec(recs: list[dict], element_id: str) -> bool:
    return any(
        r["element_id"] == element_id
        and r["triggered_rule"] == "NoMeasurableAchievementRule"
        for r in recs
    )


def test_resolve_measurable_achievement_creates_and_links(resolve_profile: str) -> None:
    """Resolving a measurable achievement persists it in the canonical profile and clears the recommendation."""
    analysis = client.post("/analyze", json={"profileId": resolve_profile})
    assert _has_measurable_achievement_rec(
        analysis.json()["recommendations"], "exp-no-tech"
    )

    response = client.post(
        f"/profiles/{resolve_profile}/resolve",
        json={
            "triggeredRule": "NoMeasurableAchievementRule",
            "elementId": "exp-no-tech",
            "skillIds": ["skill-python"],
            "experienceIds": [],
            "technologies": [],
            "achievementStatement": "Reduced deployment time by 60%",
        },
    )
    assert response.status_code == 200

    canonical = _read_canonical(resolve_profile)
    exp = next(e for e in canonical["experiences"] if e["id"] == "exp-no-tech")
    assert len(exp["achievementRefs"]) == 1
    achievement_id = exp["achievementRefs"][0]["id"]
    assert exp["achievementRefs"][0]["type"] == "achievement"

    achievement = next(a for a in canonical["achievements"] if a["id"] == achievement_id)
    assert achievement["statement"] == "Reduced deployment time by 60%"
    assert achievement["contextRefs"] == [{"id": "exp-no-tech", "type": "experience"}]
    assert achievement["skillRefs"] == [{"id": "skill-python", "type": "skill"}]

    analysis = client.post("/analyze", json={"profileId": resolve_profile})
    assert not _has_measurable_achievement_rec(
        analysis.json()["recommendations"], "exp-no-tech"
    )


def test_resolve_measurable_achievement_requires_statement(resolve_profile: str) -> None:
    """Resolution rejects a missing achievement statement."""
    response = client.post(
        f"/profiles/{resolve_profile}/resolve",
        json={
            "triggeredRule": "NoMeasurableAchievementRule",
            "elementId": "exp-no-tech",
            "achievementStatement": "",
        },
    )
    assert response.status_code == 400
    assert response.json()["error"] == "INVALID_ACHIEVEMENT"


def test_resolve_measurable_achievement_rejects_non_measurable(resolve_profile: str) -> None:
    """Resolution rejects an achievement statement with no measurable outcome."""
    response = client.post(
        f"/profiles/{resolve_profile}/resolve",
        json={
            "triggeredRule": "NoMeasurableAchievementRule",
            "elementId": "exp-no-tech",
            "achievementStatement": "Coordinated operations across departments.",
        },
    )
    assert response.status_code == 400
    assert response.json()["error"] == "ACHIEVEMENT_NOT_MEASURABLE"


def test_resolve_measurable_achievement_adds_to_qualified_experience(resolve_profile: str) -> None:
    """Adding a measurable achievement clears the 'quantify outcomes' recommendation for an experience whose linked achievements are not measurable."""
    canonical = _read_canonical(resolve_profile)
    canonical["achievements"].append(
        {
            "id": "achievement-vague",
            "statement": "Handled day-to-day operations.",
        }
    )
    exp = next(e for e in canonical["experiences"] if e["id"] == "exp-no-tech")
    exp["achievementRefs"] = [{"id": "achievement-vague", "type": "achievement"}]

    from api.main import PROFILES_ROOT

    (PROFILES_ROOT / f"{resolve_profile}.yaml").write_text(
        yaml.safe_dump(canonical), encoding="utf-8"
    )
    analysis = client.post("/analyze", json={"profileId": resolve_profile})
    assert _has_measurable_achievement_rec(
        analysis.json()["recommendations"], "exp-no-tech"
    )

    response = client.post(
        f"/profiles/{resolve_profile}/resolve",
        json={
            "triggeredRule": "NoMeasurableAchievementRule",
            "elementId": "exp-no-tech",
            "achievementStatement": "Improved availability from 99.5% to 99.95%",
        },
    )
    assert response.status_code == 200

    canonical = _read_canonical(resolve_profile)
    exp = next(e for e in canonical["experiences"] if e["id"] == "exp-no-tech")
    assert len(exp["achievementRefs"]) == 2

    analysis = client.post("/analyze", json={"profileId": resolve_profile})
    assert not _has_measurable_achievement_rec(
        analysis.json()["recommendations"], "exp-no-tech"
    )


def test_resolve_measurable_achievement_wires_artifact_source_ref(resolve_profile: str) -> None:
    """Resolving a measurable achievement adds it to artifacts that already export the experience.

    M1.9: a resolved achievement must enter the export pipeline via the existing
    sourceRef mechanism so generated CVs render it.
    """
    canonical = _read_canonical(resolve_profile)
    canonical["artifacts"] = [
        {
            "id": "artifact-cv",
            "title": "CV",
            "artifactType": "CV",
            "sourceRefs": [
                {"id": "summary-1", "type": "professional_summary"},
                {"id": "exp-no-tech", "type": "experience"},
            ],
        },
        {
            "id": "artifact-unrelated",
            "title": "Other",
            "artifactType": "CV",
            "sourceRefs": [{"id": "skill-python", "type": "skill"}],
        },
    ]
    from api.main import PROFILES_ROOT

    (PROFILES_ROOT / f"{resolve_profile}.yaml").write_text(
        yaml.safe_dump(canonical), encoding="utf-8"
    )

    response = client.post(
        f"/profiles/{resolve_profile}/resolve",
        json={
            "triggeredRule": "NoMeasurableAchievementRule",
            "elementId": "exp-no-tech",
            "skillIds": ["skill-python"],
            "achievementStatement": "Reduced deployment time by 60% through CI/CD automation.",
        },
    )
    assert response.status_code == 200

    canonical = _read_canonical(resolve_profile)
    exp = next(e for e in canonical["experiences"] if e["id"] == "exp-no-tech")
    achievement_id = exp["achievementRefs"][0]["id"]

    cv = next(a for a in canonical["artifacts"] if a["id"] == "artifact-cv")
    achievement_refs = [r for r in cv["sourceRefs"] if r.get("id") == achievement_id]
    assert achievement_refs == [{"id": achievement_id, "type": "achievement"}]

    unrelated = next(a for a in canonical["artifacts"] if a["id"] == "artifact-unrelated")
    assert achievement_id not in [r.get("id") for r in unrelated["sourceRefs"]]


def test_resolve_measurable_achievement_source_ref_is_idempotent(resolve_profile: str) -> None:
    """Resolving an achievement never duplicates the same sourceRef entry in an artifact."""
    canonical = _read_canonical(resolve_profile)
    canonical["artifacts"] = [
        {
            "id": "artifact-cv",
            "title": "CV",
            "artifactType": "CV",
            "sourceRefs": [{"id": "exp-no-tech", "type": "experience"}],
        }
    ]
    from api.main import PROFILES_ROOT

    (PROFILES_ROOT / f"{resolve_profile}.yaml").write_text(
        yaml.safe_dump(canonical), encoding="utf-8"
    )

    payload = {
        "triggeredRule": "NoMeasurableAchievementRule",
        "elementId": "exp-no-tech",
        "achievementStatement": "Reduced deployment time by 60% through CI/CD automation.",
    }
    assert client.post(f"/profiles/{resolve_profile}/resolve", json=payload).status_code == 200
    assert client.post(f"/profiles/{resolve_profile}/resolve", json=payload).status_code == 200

    canonical = _read_canonical(resolve_profile)
    cv = next(a for a in canonical["artifacts"] if a["id"] == "artifact-cv")
    achievement_refs = [r for r in cv["sourceRefs"] if r.get("type") == "achievement"]
    assert len(achievement_refs) == len({r["id"] for r in achievement_refs})
    assert len(achievement_refs) == len(canonical["achievements"])


def test_resolve_clears_improvement_queue_item(resolve_profile: str) -> None:
    """M1.24.4: resolving a recommendation removes it from the improvement-queue endpoint."""
    queue = client.get(f"/profiles/{resolve_profile}/improvement-queue")
    assert queue.status_code == 200
    target = next(
        (item for item in queue.json() if item["rule_id"] == "recommendation_add_technologies"),
        None,
    )
    assert target is not None

    response = client.post(
        f"/profiles/{resolve_profile}/resolve",
        json={
            "triggeredRule": "ExperienceNoTechnologiesRule",
            "elementId": target["element_id"],
            "technologies": ["Python", "Terraform"],
        },
    )
    assert response.status_code == 200

    queue_after = client.get(f"/profiles/{resolve_profile}/improvement-queue")
    assert queue_after.status_code == 200
    assert not any(
        item["rule_id"] == "recommendation_add_technologies"
        and item["element_id"] == target["element_id"]
        for item in queue_after.json()
    )


def test_resolved_achievement_renders_in_tailored_cv(resolve_profile: str) -> None:
    """M1.9 acceptance: a resolved measurable achievement appears in the Tailored CV."""
    canonical = _read_canonical(resolve_profile)
    canonical["professionalSummaries"] = [{"id": "summary-1", "text": "DevSecOps engineer."}]
    canonical["artifacts"] = [
        {
            "id": "artifact-cv",
            "title": "CV",
            "artifactType": "CV",
            "sourceRefs": [
                {"id": "summary-1", "type": "professional_summary"},
                {"id": "exp-no-tech", "type": "experience"},
                {"id": "skill-python", "type": "skill"},
            ],
        }
    ]
    from api.main import PROFILES_ROOT

    (PROFILES_ROOT / f"{resolve_profile}.yaml").write_text(
        yaml.safe_dump(canonical), encoding="utf-8"
    )

    response = client.post(
        f"/profiles/{resolve_profile}/resolve",
        json={
            "triggeredRule": "NoMeasurableAchievementRule",
            "elementId": "exp-no-tech",
            "achievementStatement": "Reduced deployment time by 60% through CI/CD automation.",
        },
    )
    assert response.status_code == 200

    generated = client.post(
        "/generate/artifact",
        json={
            "profile_id": resolve_profile,
            "artifact_id": "artifact-cv",
            "output_format": "markdown",
            "job_description": "DevSecOps engineer with CI/CD automation expertise",
        },
    )
    assert generated.status_code == 200
    assert "Reduced deployment time by 60% through CI/CD automation." in generated.text
    assert generated.text.count("Reduced deployment time by 60% through CI/CD automation.") == 1

    analysis = client.post("/analyze", json={"profileId": resolve_profile})
    assert not _has_measurable_achievement_rec(
        analysis.json()["recommendations"], "exp-no-tech"
    )


def _write_cv_artifact(profile_id: str, artifact_id: str, source_refs: list[dict]) -> None:
    """Attach an artifact exporting the given sourceRefs to a canonical test profile."""
    import yaml
    from api.main import PROFILES_ROOT

    canonical = _read_canonical(profile_id)
    canonical["professionalSummaries"] = canonical.get("professionalSummaries") or [
        {"id": "summary-1", "text": "DevSecOps engineer."}
    ]
    canonical["artifacts"] = [
        {
            "id": artifact_id,
            "title": "CV",
            "artifactType": "CV",
            "sourceRefs": source_refs,
        }
    ]
    (PROFILES_ROOT / f"{profile_id}.yaml").write_text(
        yaml.safe_dump(canonical), encoding="utf-8"
    )


def _artifact_record(profile_id: str, artifact_id: str) -> dict:
    canonical = _read_canonical(profile_id)
    return next(a for a in canonical["artifacts"] if a["id"] == artifact_id)


def _regenerate(client, profile_id: str, artifact_id: str) -> "TestClientResponse":
    return client.post(
        f"/profiles/{profile_id}/artifacts/{artifact_id}/regenerate",
        json={"output_format": "markdown"},
    )


def test_resolve_marks_affected_artifact_stale(resolve_profile: str) -> None:
    """M1.10: accepting a canonical change marks artifacts that export the element as stale."""
    _write_cv_artifact(
        resolve_profile,
        "artifact-cv",
        [
            {"id": "summary-1", "type": "professional_summary"},
            {"id": "exp-no-tech", "type": "experience"},
        ],
    )

    response = client.post(
        f"/profiles/{resolve_profile}/resolve",
        json={
            "triggeredRule": "NoMeasurableAchievementRule",
            "elementId": "exp-no-tech",
            "achievementStatement": "Reduced deployment time by 60% through CI/CD automation.",
        },
    )
    assert response.status_code == 200
    cv = next(a for a in response.json()["profile"]["artifacts"] if a["id"] == "artifact-cv")
    assert cv["status"] == "stale"
    assert _artifact_record(resolve_profile, "artifact-cv")["status"] == "stale"


def test_already_applied_resolution_does_not_change_freshness(resolve_profile: str) -> None:
    """M1.10: re-applying an already-applied resolution leaves artifact freshness untouched."""
    _write_cv_artifact(
        resolve_profile,
        "artifact-cv",
        [{"id": "skill-python", "type": "skill"}],
    )

    payload = {
        "triggeredRule": "SkillWithoutExperienceRule",
        "elementId": "skill-python",
        "experienceIds": ["exp-no-tech"],
    }
    assert client.post(f"/profiles/{resolve_profile}/resolve", json=payload).status_code == 200
    assert _artifact_record(resolve_profile, "artifact-cv")["status"] == "stale"

    canonical = _read_canonical(resolve_profile)
    for art in canonical["artifacts"]:
        art["status"] = "current"
    import yaml
    from api.main import PROFILES_ROOT

    (PROFILES_ROOT / f"{resolve_profile}.yaml").write_text(
        yaml.safe_dump(canonical), encoding="utf-8"
    )

    assert client.post(f"/profiles/{resolve_profile}/resolve", json=payload).status_code == 200
    assert _artifact_record(resolve_profile, "artifact-cv")["status"] == "current"


def test_regenerate_clears_stale_flag(resolve_profile: str) -> None:
    """M1.10: explicit regeneration clears the stale flag and returns fresh markdown."""
    _write_cv_artifact(
        resolve_profile,
        "artifact-cv",
        [
            {"id": "summary-1", "type": "professional_summary"},
            {"id": "exp-no-tech", "type": "experience"},
            {"id": "skill-python", "type": "skill"},
        ],
    )
    response = client.post(
        f"/profiles/{resolve_profile}/resolve",
        json={
            "triggeredRule": "NoMeasurableAchievementRule",
            "elementId": "exp-no-tech",
            "achievementStatement": "Reduced deployment time by 60% through CI/CD automation.",
        },
    )
    assert response.status_code == 200
    assert _artifact_record(resolve_profile, "artifact-cv")["status"] == "stale"

    regenerated = _regenerate(client, resolve_profile, "artifact-cv")
    assert regenerated.status_code == 200
    body = regenerated.json()
    assert body["artifactId"] == "artifact-cv"
    assert body["status"] == "current"
    assert body["output_format"] == "markdown"
    assert _artifact_record(resolve_profile, "artifact-cv")["status"] == "current"


def test_regenerated_artifact_contains_accepted_achievement(resolve_profile: str) -> None:
    """M1.10: the regenerated artifact renders the accepted achievement exactly once."""
    _write_cv_artifact(
        resolve_profile,
        "artifact-cv",
        [
            {"id": "summary-1", "type": "professional_summary"},
            {"id": "exp-no-tech", "type": "experience"},
            {"id": "skill-python", "type": "skill"},
        ],
    )
    response = client.post(
        f"/profiles/{resolve_profile}/resolve",
        json={
            "triggeredRule": "NoMeasurableAchievementRule",
            "elementId": "exp-no-tech",
            "achievementStatement": "Reduced deployment time by 60% through CI/CD automation.",
        },
    )
    assert response.status_code == 200

    regenerated = _regenerate(client, resolve_profile, "artifact-cv")
    assert regenerated.status_code == 200
    markdown = regenerated.json()["artifact"]
    assert "Reduced deployment time by 60% through CI/CD automation." in markdown
    assert markdown.count("Reduced deployment time by 60% through CI/CD automation.") == 1

    achievement_refs = [
        r for r in _artifact_record(resolve_profile, "artifact-cv")["sourceRefs"]
        if r.get("type") == "achievement"
    ]
    assert len(achievement_refs) == 1


def test_existing_artifact_unchanged_until_regeneration(resolve_profile: str) -> None:
    """M1.10: resolution never mutates the artifact record itself; only regeneration refreshes it."""
    _write_cv_artifact(
        resolve_profile,
        "artifact-cv",
        [
            {"id": "summary-1", "type": "professional_summary"},
            {"id": "exp-no-tech", "type": "experience"},
        ],
    )
    baseline = client.post(
        "/generate/artifact",
        json={
            "profile_id": resolve_profile,
            "artifact_id": "artifact-cv",
            "output_format": "markdown",
        },
    )
    assert baseline.status_code == 200
    assert "Coordinated operations across several departments." in baseline.text

    before = _artifact_record(resolve_profile, "artifact-cv")
    response = client.post(
        f"/profiles/{resolve_profile}/resolve",
        json={
            "triggeredRule": "ExperienceNoTechnologiesRule",
            "elementId": "exp-no-tech",
            "technologies": ["python"],
        },
    )
    assert response.status_code == 200

    after = _artifact_record(resolve_profile, "artifact-cv")
    assert after["id"] == before["id"]
    assert after["title"] == before["title"]
    assert after["sourceRefs"] == before["sourceRefs"]
    assert after["status"] == "stale"

    regenerated = _regenerate(client, resolve_profile, "artifact-cv")
    assert regenerated.status_code == 200
    assert "python" in regenerated.json()["artifact"].lower()
    assert _artifact_record(resolve_profile, "artifact-cv")["status"] == "current"


def test_artifact_lifecycle_end_to_end(resolve_profile: str) -> None:
    """M1.10: generate -> accept -> stale -> regenerate -> current end-to-end workflow."""
    _write_cv_artifact(
        resolve_profile,
        "artifact-cv",
        [
            {"id": "summary-1", "type": "professional_summary"},
            {"id": "exp-no-tech", "type": "experience"},
        ],
    )

    baseline = client.post(
        "/generate/artifact",
        json={
            "profile_id": resolve_profile,
            "artifact_id": "artifact-cv",
            "output_format": "markdown",
        },
    )
    assert baseline.status_code == 200
    assert "Reduced deployment time by 60%" not in baseline.text

    accepted = client.post(
        f"/profiles/{resolve_profile}/resolve",
        json={
            "triggeredRule": "NoMeasurableAchievementRule",
            "elementId": "exp-no-tech",
            "achievementStatement": "Reduced deployment time by 60% through CI/CD automation.",
        },
    )
    assert accepted.status_code == 200
    cv = next(a for a in accepted.json()["profile"]["artifacts"] if a["id"] == "artifact-cv")
    assert cv["status"] == "stale"
    assert _artifact_record(resolve_profile, "artifact-cv")["status"] == "stale"

    current = _regenerate(client, resolve_profile, "artifact-cv")
    assert current.status_code == 200
    body = current.json()
    assert body["status"] == "current"
    assert "Reduced deployment time by 60% through CI/CD automation." in body["artifact"]
    assert body["artifact"].count("Reduced deployment time by 60% through CI/CD automation.") == 1
    assert _artifact_record(resolve_profile, "artifact-cv")["status"] == "current"


def test_create_interest_letter_artifact(tmp_path: Path) -> None:
    """POST /profiles/{id}/artifacts with the interest letter template creates a valid artifact.

    Regression test covering:
    * template registration
    * artifactType == INTEREST_LETTER
    * expected sourceRefs (only professional_summary, experience, skill, education)
    * successful API-based artifact creation
    """
    from api.main import PROFILES_ROOT

    profile_id = "test-interest-letter-artifact"
    profile_data = {
        "profileVersion": "1.0.0",
        "person": {"id": "person-123"},
        "professionalSummaries": [{"id": "sum-1", "text": "Experienced engineer."}],
        "experiences": [{"id": "exp-1", "title": "Senior Engineer"}],
        "skills": [{"id": "skill-1", "name": "Python"}],
        "education": [{"id": "edu-1", "program": "MSc CS"}],
        "certifications": [{"id": "cert-1", "name": "AWS Certified"}],
        "projects": [{"id": "proj-1", "name": "Platform Alpha"}],
        "achievements": [{"id": "ach-1", "name": "Award"}],
        "artifacts": [],
    }
    profile_path = PROFILES_ROOT / f"{profile_id}.yaml"
    try:
        profile_path.write_text(yaml.safe_dump(profile_data), encoding="utf-8")

        response = client.post(
            f"/profiles/{profile_id}/artifacts",
            json={"template": "standard_interest_letter"},
        )
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

        body = response.json()
        assert body["artifactId"].startswith("artf-standard_interest_letter-person-123")

        artifact = body["artifact"]
        assert artifact["artifactType"] == "INTEREST_LETTER"
        assert artifact["title"] == "Interest Letter"

        source_refs = artifact["sourceRefs"]
        assert len(source_refs) == 4
        source_types = {r["type"] for r in source_refs}
        assert source_types == {"professional_summary", "experience", "skill", "education"}
    finally:
        if profile_path.exists():
            profile_path.unlink()
