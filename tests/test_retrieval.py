"""Tests for RetrievalService."""

import pytest
from sqlalchemy.orm import Session

from app.db.session import Base, SessionLocal, engine
from app.db.seed import seed_database
from app.services.retrieval import RetrievalService, extract_constituency


@pytest.fixture(scope="module")
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    seed_database(session)
    yield session
    session.close()


def test_extract_constituency():
    assert extract_constituency("is there a hospital in Likoni?") == "Likoni"
    assert extract_constituency("Road project in Mvita constituency") == "Mvita"
    assert extract_constituency("hello world") is None


def test_search_infrastructure_by_constituency(db: Session):
    retrieval_svc = RetrievalService(db)
    results = retrieval_svc.search_infrastructure(query="Hospital", constituency="Likoni")
    assert isinstance(results, list)
    for item in results:
        assert item["constituency"] == "Likoni"


def test_is_there_a_hospital_in_likoni(db: Session):
    retrieval_svc = RetrievalService(db)
    res = retrieval_svc.search_all(query="is there a hospital in Likoni?")
    assert res["constituency"] == "Likoni"
    infra = res["infrastructure"]
    assert len(infra) > 0
    assert any("Hospital" in item["name"] or "Hospital" in item["type"] for item in infra)
    assert infra[0]["constituency"] == "Likoni"


def test_broken_bridge_in_likoni_ranks_likoni_first(db: Session):
    retrieval_svc = RetrievalService(db)
    res = retrieval_svc.search_all(query="broken bridge in Likoni")
    assert res["constituency"] == "Likoni"
    infra = res["infrastructure"]
    assert len(infra) > 0
    assert infra[0]["name"] == "Likoni Floating Footbridge"
    assert infra[0]["constituency"] == "Likoni"


def test_search_projects(db: Session):
    retrieval_svc = RetrievalService(db)
    results = retrieval_svc.search_projects(query="Road", constituency="Mvita")
    assert isinstance(results, list)
    if results:
        assert "name" in results[0]
        assert "status" in results[0]


def test_search_submissions(db: Session):
    retrieval_svc = RetrievalService(db)
    results = retrieval_svc.search_submissions(query="water")
    assert isinstance(results, list)


def test_search_issues(db: Session):
    retrieval_svc = RetrievalService(db)
    results = retrieval_svc.search_issues(query="water")
    assert isinstance(results, list)


def test_search_all_returns_ranked_results(db: Session):
    retrieval_svc = RetrievalService(db)
    res = retrieval_svc.search_all(query="school", constituency="Nyali", limit=5)
    assert "query" in res
    assert "infrastructure" in res
    assert "projects" in res
    assert "submissions" in res
    assert "issues" in res
    assert "total_matches" in res
