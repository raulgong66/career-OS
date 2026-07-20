from fastapi.testclient import TestClient

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
