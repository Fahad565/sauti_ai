"""Smoke test for the root endpoint."""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root_returns_service_status() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"service": "Sauti AI", "status": "running"}
