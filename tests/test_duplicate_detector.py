"""Tests for Sprint 6 Feature 6.2 DuplicateDetector."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.services.duplicate_detector import DuplicateDetector


@pytest.fixture
def memory_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _insert_submission(db, content, constituency=None, ward=None):
    from app.models.domain import User, Submission, ConversationSession

    user = User(phone_number=f"+2547{uuid_digits()}", name="X", constituency=constituency)
    db.add(user)
    db.flush()
    sess = ConversationSession(user_id=user.id, channel="whatsapp", status="active")
    db.add(sess)
    db.flush()
    sub = Submission(
        session_id=sess.id,
        user_id=user.id,
        raw_content=content,
        constituency=constituency,
        ward=ward,
        status="received",
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def uuid_digits():
    """Naive unique-ish 9 digit suffix to avoid phone-number clashes."""
    import time

    return f"{int(time.time() * 1000) % 1_000_000_000:09d}"


def test_empty_text_is_not_duplicate(memory_db):
    det = DuplicateDetector(memory_db)
    result = det.detect("")
    assert result.is_duplicate is False
    assert result.best_match_id is None
    assert result.best_similarity == 0.0


def test_no_history_is_not_duplicate(memory_db):
    det = DuplicateDetector(memory_db)
    result = det.detect("There is no water in Majengo")
    assert result.is_duplicate is False


def test_exact_duplicate_is_detected(memory_db):
    sub = _insert_submission(
        memory_db,
        "There are potholes on Moi Avenue",
        constituency="Mvita",
    )
    det = DuplicateDetector(memory_db)
    result = det.detect("There are potholes on Moi Avenue", constituency="Mvita")
    assert result.is_duplicate is True
    assert result.best_match_id == sub.id
    assert result.best_similarity >= 0.60


def test_paraphrased_duplicate_is_detected(memory_db):
    _insert_submission(
        memory_db,
        "There are potholes on Moi Avenue in Mvita",
        constituency="Mvita",
    )
    det = DuplicateDetector(memory_db, threshold=0.55)
    result = det.detect("Moi Avenue in Mvita has many potholes", constituency="Mvita")
    # Even though the wording is reordered, the duplicate detector
    # should still flag it as a duplicate with a high similarity score.
    assert result.is_duplicate is True
    assert result.best_similarity >= 0.55


def test_unrelated_submission_is_not_duplicate(memory_db):
    _insert_submission(
        memory_db,
        "Garbage has piled up near the stadium",
        constituency="Mvita",
    )
    det = DuplicateDetector(memory_db)
    result = det.detect(
        "There are no teachers at Likoni primary school",
        constituency="Likoni",
    )
    assert result.is_duplicate is False


def test_constituency_filter_restricts_search(memory_db):
    _insert_submission(
        memory_db,
        "Potholes all over Moi Avenue",
        constituency="Mvita",
    )
    det = DuplicateDetector(memory_db, threshold=0.40)
    # Same wording but searching only Likoni, so the Mvita row is excluded.
    result = det.detect(
        "Potholes all over Moi Avenue",
        constituency="Likoni",
    )
    assert result.is_duplicate is False


def test_similarity_helper_returns_high_for_same_text():
    det = DuplicateDetector.__new__(DuplicateDetector)
    sim = det.similarity("pothole on Moi Avenue", "pothole on Moi Avenue")
    assert sim >= 0.95


def test_similarity_helper_returns_low_for_unrelated():
    det = DuplicateDetector.__new__(DuplicateDetector)
    sim = det.similarity("hospital needs doctors", "garbage in the market")
    assert sim < 0.40


def test_match_contains_trigram_and_token_jaccard(memory_db):
    _insert_submission(
        memory_db,
        "Water has been off in Majengo for three days",
        constituency="Mvita",
    )
    det = DuplicateDetector(memory_db)
    result = det.detect(
        "Water has been off in Majengo for three days",
        constituency="Mvita",
    )
    assert result.is_duplicate
    match = result.matches[0]
    assert match.token_jaccard >= 0.5
    assert match.trigram_jaccard >= 0.5


def test_time_window_excludes_old_submissions(memory_db):
    from datetime import datetime, timedelta, timezone

    # Insert submission directly with an old timestamp
    from app.models.domain import User, Submission, ConversationSession

    user = User(phone_number="+254700000001", name="Old", constituency="Likoni")
    memory_db.add(user)
    memory_db.flush()
    sess = ConversationSession(user_id=user.id, channel="whatsapp", status="active")
    memory_db.add(sess)
    memory_db.flush()
    old_sub = Submission(
        session_id=sess.id,
        user_id=user.id,
        raw_content="Potholes on Moi Avenue in Mombasa",
        constituency="Likoni",
        status="received",
    )
    memory_db.add(old_sub)
    memory_db.commit()
    # Backdate it to 60 days ago
    memory_db.query(Submission).filter(Submission.id == old_sub.id).update(
        {"submitted_at": datetime.now(timezone.utc) - timedelta(days=60)}
    )
    memory_db.commit()

    det = DuplicateDetector(memory_db, time_window_days=7)
    result = det.detect(
        "Potholes on Moi Avenue in Mombasa",
        constituency="Likoni",
    )
    # Old submission was outside the 7-day window -> not a duplicate.
    assert result.is_duplicate is False
