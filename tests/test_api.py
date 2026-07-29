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
    assert "- AI workflow design" in response.text


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
    assert "- AI workflow design" in response.text


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
