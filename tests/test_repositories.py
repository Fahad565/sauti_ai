"""Tests for repository layer CRUD operations."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.repositories import (
    UserRepository,
    SessionRepository,
    SubmissionRepository,
    InfrastructureRepository,
    ProjectRepository,
    IssueRepository,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_user_repository(db):
    repo = UserRepository(db)
    user = repo.get_or_create(phone_number="+254711223344", name="Amina")
    assert user.id is not None
    assert user.name == "Amina"

    fetched = repo.get_by_phone("+254711223344")
    assert fetched is not None
    assert fetched.id == user.id



def test_infrastructure_repository_filtering(db):
    repo = InfrastructureRepository(db)
    repo.create({"constituency": "Likoni", "name": "Likoni Hospital", "type": "Hospitals", "status": "operational"})
    repo.create({"constituency": "Mvita", "name": "Mvita Clinic", "type": "Hospitals", "status": "operational"})
    repo.create({"constituency": "Likoni", "name": "Likoni Road", "type": "Roads", "status": "operational"})

    likoni_assets = repo.list_by_constituency("Likoni")
    assert len(likoni_assets) == 2

    hospitals = repo.list_by_type("Hospitals")
    assert len(hospitals) == 2


def test_project_repository_filtering(db):
    repo = ProjectRepository(db)
    repo.create({"constituency": "Kisauni", "name": "Bypass Road", "type": "Roads", "status": "Ongoing", "budget": 10000.0})
    repo.create({"constituency": "Kisauni", "name": "Water Kiosk", "type": "Water", "status": "Completed", "budget": 5000.0})

    ongoing = repo.list_by_status("Ongoing")
    assert len(ongoing) == 1
    assert ongoing[0].name == "Bypass Road"
