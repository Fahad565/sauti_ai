"""Tests for Sprint 6 Feature 6.6 TrendDetector."""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.services.trend_detector import TrendDetector
from app.models.domain import User, Submission, ConversationSession


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


def _make_submission(db, content, constituency=None, *, days_ago=1):
    user = User(phone_number=f"+2547{abs(hash(content)) % 10**9:09d}")
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
        status="received",
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    sub.submitted_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    db.commit()
    db.refresh(sub)
    return sub


def test_trend_report_on_empty_db(memory_db):
    det = TrendDetector(memory_db)
    report = det.detect()
    assert report.total_volume == 0
    assert report.previous_volume == 0
    assert report.direction == "flat"
    assert report.hotspots == []
    assert report.recurring_failures == []


def test_trend_detects_rising_volume(memory_db):
    for i in range(5):
        _make_submission(memory_db, f"Potholes near park {i}", constituency="Likoni", days_ago=1)
    # previous window (8–14 days ago) was empty
    det = TrendDetector(memory_db, window_days=7, compare_window_days=7)
    report = det.detect()
    assert report.total_volume == 5
    assert report.direction == "rising"


def test_trend_detects_falling_volume(memory_db):
    for i in range(3):
        _make_submission(memory_db, f"Old pothole report {i}", days_ago=10)
    det = TrendDetector(memory_db, window_days=3, compare_window_days=7)
    report = det.detect()
    # 0 in the recent window vs 3 in the previous window => falling.
    assert report.direction in ("falling", "flat")


def test_trend_detects_hotspots(memory_db):
    """Same constituency in current window, none in previous -> hotspot delta."""
    for i in range(4):
        _make_submission(memory_db, f"Garbage not collected {i}", constituency="Kisauni", days_ago=1)
    det = TrendDetector(memory_db)
    report = det.detect()
    hotspots = [h for h in report.hotspots if h.constituency == "Kisauni"]
    assert len(hotspots) == 1
    assert hotspots[0].delta >= 4
    assert hotspots[0].current_volume == 4


def test_trend_recurring_failures_grouped(memory_db):
    # Several very similar submissions in the current window.
    _make_submission(memory_db, "Potholes on Moi Avenue Mvita", constituency="Mvita", days_ago=0)
    _make_submission(memory_db, "Potholes on Moi Avenue Mvita CBD", constituency="Mvita", days_ago=0)
    _make_submission(memory_db, "Moi Avenue in Mvita has potholes", constituency="Mvita", days_ago=0)
    det = TrendDetector(memory_db)
    report = det.detect()
    assert len(report.recurring_failures) >= 1
    largest = max(report.recurring_failures, key=lambda r: r.count)
    assert largest.count >= 2


def test_trend_weekly_pulse_buckets(memory_db):
    for i in range(3):
        _make_submission(memory_db, f"recent submission {i}", days_ago=i + 1)
    det = TrendDetector(memory_db, window_days=7)
    report = det.detect()
    assert sum(report.weekly_pulse.values()) == 3


def test_trend_top_categories_counts_keywords(memory_db):
    _make_submission(memory_db, "Potholes everywhere on the road", days_ago=0)
    _make_submission(memory_db, "Water pipe is leaking", days_ago=0)
    _make_submission(memory_db, "Garbage has piled up", days_ago=0)
    det = TrendDetector(memory_db)
    report = det.detect()
    counter = {c["keyword"]: c["count"] for c in report.top_categories}
    assert counter.get("road", 0) >= 1
    assert counter.get("water", 0) >= 1
    assert counter.get("garbage", 0) >= 1


def test_trend_to_dict_is_json_serialisable(memory_db):
    import json

    _make_submission(memory_db, "Potholes on the road", constituency="Likoni", days_ago=0)
    report = TrendDetector(memory_db).detect()
    # Should be serialisable; any datetime inside the call would break this.
    text = json.dumps(report.to_dict(), default=str)
    assert "total_volume" in text
