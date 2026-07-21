from pathlib import Path

from fastapi.testclient import TestClient
import yaml

from api.main import app


client = TestClient(app)


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
