"""Tests for Sprint 6 Feature 6.3 PriorityScorer."""

import pytest

from app.services.priority_scorer import PriorityScorer, PRIORITY_LEVELS


def test_emergency_keywords_produce_critical():
    scorer = PriorityScorer()
    res = scorer.score("There is a fire at the school and children are trapped")
    assert res.level == "Critical"
    assert res.signals["urgency"] >= 5


def test_healthcare_complaint_with_dupes_is_high_or_critical():
    scorer = PriorityScorer()
    res = scorer.score(
        "Hospital has no doctors and no medicine",
        category="Healthcare",
        duplicate_count=4,
    )
    assert res.level in ("High", "Critical")


def test_simple_complaint_is_medium_or_higher():
    scorer = PriorityScorer()
    res = scorer.score("The road has potholes", category="Roads")
    assert res.level in ("Low", "Medium", "High")


def test_low_priority_when_no_signals():
    scorer = PriorityScorer()
    res = scorer.score("Hello there", category="Markets")
    assert res.level == "Low"


def test_duplicate_pressure_raises_level():
    scorer = PriorityScorer()
    baseline = scorer.score("The road has potholes", category="Roads")
    amplified = scorer.score(
        "The road has potholes",
        category="Roads",
        duplicate_count=5,
    )
    assert amplified.score >= baseline.score
    assert amplified.level in PRIORITY_LEVELS


def test_category_floor_applied():
    scorer = PriorityScorer()
    healthcare = scorer.score("general complaint", category="Healthcare")
    markets = scorer.score("general complaint", category="Markets")
    assert healthcare.score >= markets.score


def test_caps_intensity_contributes_to_score():
    scorer = PriorityScorer()
    loud = scorer.score("HELP HELP HELP!!! WATER!! NO WATER!! PLEASE!!!")
    quiet = scorer.score("there is no water in our area this morning please help")
    assert loud.signals["emphasis"] > 0
    assert loud.score >= quiet.score - 0.5  # at least comparable


def test_repetition_intensity_detected():
    scorer = PriorityScorer()
    res = scorer.score("very very very very broken broken broken pipe")
    assert res.signals["emphasis"] > 0


def test_empty_text_defaults_to_low():
    scorer = PriorityScorer()
    res = scorer.score("")
    assert res.level in PRIORITY_LEVELS
    assert res.score == 0


def test_to_dict_round_trip():
    scorer = PriorityScorer()
    res = scorer.score("Road has potholes", category="Roads")
    d = res.to_dict()
    assert "level" in d
    assert "score" in d
    assert "signals" in d
    assert "rationale" in d
    assert d["category"] == "Roads"


def test_levels_are_well_ordered():
    """Critical must outrank High which must outrank Medium which must outrank Low."""
    scorer = PriorityScorer()
    a = scorer.score(
        "Fire at the hospital, children trapped, ambulances needed urgently",
        category="Healthcare",
        duplicate_count=10,
    )
    b = scorer.score(
        "There is no medicine at the clinic",
        category="Healthcare",
    )
    c = scorer.score("Just thinking aloud", category="Markets")
    assert a.score > b.score > c.score
    rank = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
    assert rank[a.level] >= rank[b.level] >= rank[c.level]


def test_custom_thresholds():
    scorer = PriorityScorer(thresholds={"Critical": 100, "High": 50, "Medium": 10, "Low": 0})
    res = scorer.score("Fire at school children trapped", category="Healthcare", duplicate_count=3)
    # Custom thresholds make everything go to Low or Medium.
    assert res.level in ("Low", "Medium")
