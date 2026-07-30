"""Tests for database connections, models, and session management."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.domain import (
    User,
    ConversationSession,
    Submission,
    Issue,
    Cluster,
    Infrastructure,
    Project,
    AgentAction,
    AISummary,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_models_creation(db_session):
    """Test creation and relationship linking for core models."""
    user = User(phone_number="+254700000001", name="Test Citizen", constituency="Mvita")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.id is not None

    conv = ConversationSession(user_id=user.id, channel="whatsapp")
    db_session.add(conv)
    db_session.commit()
    db_session.refresh(conv)

    assert conv.user.name == "Test Citizen"

    sub = Submission(session_id=conv.id, user_id=user.id, raw_content="Water pipe burst near school")
    db_session.add(sub)
    db_session.commit()

    assert len(list(user.submissions)) == 1  # type: ignore[arg-type]
    assert sub.user.phone_number == "+254700000001"


def test_infrastructure_and_projects(db_session):
    """Test Infrastructure and Project creation."""
    infra = Infrastructure(constituency="Nyali", name="Kongowea Bridge", type="Bridges", status="operational")
    proj = Project(constituency="Nyali", name="Market Expansion", type="Commerce", status="Ongoing", budget=50000.0)

    db_session.add_all([infra, proj])
    db_session.commit()

    assert db_session.query(Infrastructure).count() == 1
    assert db_session.query(Project).count() == 1
