"""Tests for persistence service and seed data initialization."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.db.seed import seed_database
from app.services.persistence import record_inbound_message, record_agent_execution
from app.models.domain import Infrastructure, Project, Submission, AgentAction, AISummary


@pytest.fixture
def memory_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_seed_database(memory_db):
    seed_database(memory_db)
    infra_count = memory_db.query(Infrastructure).count()
    project_count = memory_db.query(Project).count()

    assert infra_count == 42
    assert project_count == 18

    # Re-running seed should not duplicate records
    seed_database(memory_db)
    assert memory_db.query(Infrastructure).count() == 42


def test_record_inbound_and_agent_execution(memory_db):
    user, session, submission = record_inbound_message(
        phone_number="+254788112233",
        raw_content="Need more desks in Likoni primary school",
        user_name="Fatuma",
        db=memory_db,
    )

    assert user.phone_number == "+254788112233"
    assert submission.raw_content == "Need more desks in Likoni primary school"

    final_state = {
        "input_message": "Need more desks in Likoni primary school",
        "steps": ["intake", "analyze", "respond"],
        "analysis": "Citizen requests desks for Likoni Primary School in Likoni. Priority: Medium.",
        "response": "Citizen requests desks for Likoni Primary School in Likoni. Priority: Medium.",
        "metadata": {"analyze_provider": "google"},
    }

    record_agent_execution(int(session.id), int(submission.id), final_state, db=memory_db)  # type: ignore[arg-type]


    actions = memory_db.query(AgentAction).filter(AgentAction.submission_id == submission.id).all()
    summaries = memory_db.query(AISummary).filter(AISummary.submission_id == submission.id).all()

    assert len(actions) == 1
    assert len(summaries) == 1
    assert "Likoni Primary School" in summaries[0].summary_text
