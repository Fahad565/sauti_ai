"""Tests for Sprint 6 Feature 6.1 CivicClassifier."""

import pytest

from app.services.civic_classifier import (
    CivicClassifier,
    CIVIC_CATEGORIES,
)


# --- Happy-path categories ---


@pytest.mark.parametrize(
    "text, expected",
    [
        ("The Likoni road has terrible potholes", "Roads"),
        ("My child was injured by a broken streetlight", "Roads"),
        ("Coast General Hospital has no doctors on duty", "Healthcare"),
        ("There is cholera outbreak in Old Town, send ambulances", "Healthcare"),
        ("We have had no water for three days", "Water"),
        ("Pipes are leaking in Majengo", "Water"),
        ("Our primary school has no teachers", "Education"),
        ("Pupils are learning under trees because the school has no classrooms", "Education"),
        ("Kongowea market traders are fighting", "Markets"),
        ("Sewer has overflowed onto the main road", "Sanitation"),
        ("Garbage has piled up for two weeks", "Sanitation"),
        ("There are robbers at the Kipevu stage", "Security"),
        ("Trees have been cut down near the creek", "Environment"),
        ("Flooding destroyed many houses in Mombasa", "Environment"),
        ("The rental houses have leaking roofs", "Housing"),
        ("Likoni matatus are overcharging", "Transport"),
    ],
)
def test_classify_each_civic_category(text, expected):
    classifier = CivicClassifier()
    result = classifier.classify(text)
    assert result.category == expected
    assert 0.0 <= result.confidence <= 1.0
    assert isinstance(result.matched_keywords, list)


def test_empty_text_returns_safe_default():
    res = CivicClassifier().classify("")
    assert res.category == "Sanitation"
    assert res.confidence == 0.0


def test_whitespace_only_returns_safe_default():
    res = CivicClassifier().classify("    ")
    assert res.category == "Sanitation"
    assert res.confidence == 0.0


def test_unknown_text_returns_low_confidence_default():
    res = CivicClassifier().classify("zzzzz qqqq xxxx")
    assert res.category == "Sanitation"
    assert res.confidence <= 0.35


def test_scores_are_per_category():
    text = "the road has potholes and water is leaking from a broken pipe"
    res = CivicClassifier().classify(text)
    assert set(res.scores.keys()) == set(CIVIC_CATEGORIES)
    # The Roads and Water categories should both have non-zero scores.
    assert res.scores["Roads"] > 0
    assert res.scores["Water"] > 0


def test_confidence_capped_at_0_95():
    """A long stuffed text should still cap at 0.95, not produce >1 values."""
    text = (
        "hospital clinic dispensary doctor nurse patient maternity casualty "
        "ambulance medical pharmacy vaccination health medicine"
    )
    res = CivicClassifier().classify(text)
    assert res.confidence <= 0.95


def test_to_dict_round_trip():
    res = CivicClassifier().classify("Potholes on Moi Avenue")
    d = res.to_dict()
    assert d["category"] == "Roads"
    assert "matched_keywords" in d
    assert "scores" in d


def test_classify_batch_returns_list():
    classifier = CivicClassifier()
    results = classifier.classify_batch(["Pothole near Kongowea", "Doctor on strike"])
    assert len(results) == 2
    assert results[0].category == "Roads"
    assert results[1].category == "Healthcare"
