"""Tests for RESTful CRUD API endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.db.session import Base, get_db


@pytest.fixture
def client_with_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client


def test_crud_users_api(client_with_db):
    res = client_with_db.post("/api/v1/users", json={
        "phone_number": "+254799999999",
        "name": "API User",
        "constituency": "Jomvu",
        "ward": "Mikindani"
    })
    assert res.status_code == 201
    data = res.json()
    assert data["id"] is not None
    user_id = data["id"]

    res = client_with_db.get("/api/v1/users")
    assert res.status_code == 200
    users = res.json()
    assert any(u["id"] == user_id for u in users)

    res = client_with_db.get(f"/api/v1/users/{user_id}")
    assert res.status_code == 200
    assert res.json()["name"] == "API User"


def test_crud_infrastructure_api(client_with_db):
    res = client_with_db.post("/api/v1/infrastructure", json={
        "constituency": "Changamwe",
        "name": "Changamwe Water Kiosk",
        "type": "Water points",
        "status": "operational",
        "location": "Airport Ward"
    })
    assert res.status_code == 201
    infra_id = res.json()["id"]

    res = client_with_db.get("/api/v1/infrastructure?constituency=Changamwe")
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 1
    assert any(i["name"] == "Changamwe Water Kiosk" for i in items)


def test_crud_projects_api(client_with_db):
    res = client_with_db.post("/api/v1/projects", json={
        "constituency": "Nyali",
        "name": "Nyali Solar Lighting",
        "type": "Energy",
        "status": "Ongoing",
        "budget": 150000.0,
        "description": "Solar street lamps installation"
    })
    assert res.status_code == 201
    assert res.json()["budget"] == 150000.0

    res = client_with_db.get("/api/v1/projects?status=Ongoing")
    assert res.status_code == 200
    projects = res.json()
    assert any(p["name"] == "Nyali Solar Lighting" for p in projects)
