"""Tests for Sprint 6 Feature 6.7 endpoints and orchestrator."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.main import app


@pytest.fixture
def memory_db():
    """A single in-memory SQLite DB shared across threads.

    ``StaticPool`` keeps one connection alive for the whole process so
    the FastAPI TestClient (which runs requests on a worker thread)
    shares the same DB the test created.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(memory_db):
    """FastAPI TestClient with the get_db dependency overridden to in-memory DB."""

    def override_get_db():
        try:
            yield memory_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_pipeline_health(client):
    resp = client.get("/api/v1/pipeline/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["pipeline_version"] == "sprint-6"


def test_classify_endpoint(client):
    resp = client.post(
        "/api/v1/pipeline/classify",
        json={"text": "There are potholes on Moi Avenue"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["category"] == "Roads"
    assert body["confidence"] > 0.0


def test_duplicate_detection_endpoint_no_history(client):
    resp = client.post(
        "/api/v1/pipeline/duplicates",
        json={"text": "Potholes on Moi Avenue", "constituency": "Mvita"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_duplicate"] is False
    assert body["matches"] == []


def test_priority_endpoint_emergency(client):
    resp = client.post(
        "/api/v1/pipeline/priority",
        json={"text": "Fire at school, children trapped, ambulance needed", "constituency": "Likoni"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["level"] in ("High", "Critical")


def test_geography_endpoint_extracts_landmark(client):
    resp = client.post(
        "/api/v1/pipeline/geography",
        json={"text": "Likoni Floating Footbridge is collapsing"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "Likoni Floating Footbridge" in body["landmarks"]
    assert body["constituency"] == "Likoni"


def test_topics_endpoint_returns_tags(client):
    resp = client.post(
        "/api/v1/pipeline/topics",
        json={"text": "There is a fire at the school with children trapped"},
    )
    assert resp.status_code == 200
    body = resp.json()
    tag_names = {t["tag"] for t in body["tags"]}
    assert "Safety" in tag_names or "Schools" in tag_names or "Children" in tag_names


def test_full_pipeline_run(client):
    resp = client.post(
        "/api/v1/pipeline/run",
        json={
            "text": "The road towards Nyali from Buxton is very poor with potholes",
            "constituency": "Nyali",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["text"].startswith("The road towards Nyali")
    assert body["classification"]["category"] in ("Roads",)
    assert body["geography"]["constituency"] == "Nyali"
    assert "Roads" in {t["tag"] for t in body["topics"]["tags"]}


def test_pipeline_run_with_trend(client):
    resp = client.post(
        "/api/v1/pipeline/run",
        json={
            "text": "Garbage piling up at Kongowea market",
            "include_trend": True,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["trend"] is not None
    assert "total_volume" in body["trend"]


def test_empty_text_validation(client):
    resp = client.post(
        "/api/v1/pipeline/classify",
        json={"text": ""},
    )
    # Pydantic should reject empty text via min_length=1
    assert resp.status_code == 422


def test_missing_text_field(client):
    resp = client.post("/api/v1/pipeline/classify", json={"constituency": "Likoni"})
    assert resp.status_code == 422
