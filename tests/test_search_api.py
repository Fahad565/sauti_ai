"""Integration tests for Search API endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_unified_search_endpoint(client: TestClient):
    response = client.get("/api/v1/search?q=hospital&constituency=Likoni")
    assert response.status_code == 200
    data = response.json()
    assert "infrastructure" in data
    assert "projects" in data
    assert "submissions" in data
    assert "issues" in data


def test_search_projects_endpoint(client: TestClient):
    response = client.get("/api/v1/projects/search?q=road&constituency=Mvita")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_search_infrastructure_endpoint(client: TestClient):
    response = client.get("/api/v1/infrastructure/search?q=school")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
