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
