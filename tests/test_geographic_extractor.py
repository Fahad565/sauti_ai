"""Tests for Sprint 6 Feature 6.4 GeographicExtractor."""

import pytest

from app.services.geographic_extractor import GeographicExtractor, COUNTIES, CONSTITUENCIES


def test_extractor_recognises_constituency_in_text():
    geo = GeographicExtractor()
    res = geo.extract("There are potholes in Likoni road")
    assert res.constituency == "Likoni"
    assert res.fallback_used is False
    assert res.confidence >= 0.5


def test_extractor_recognises_road_reference():
    geo = GeographicExtractor()
    res = geo.extract("The Moi Avenue drainage is blocked")
    assert "Moi Avenue" in res.roads
    assert res.county == "Mombasa"


def test_extractor_recognises_facility_reference():
    geo = GeographicExtractor()
    res = geo.extract("Coast General Hospital has run out of medicine")
    assert "Coast General Hospital" in res.facilities


def test_extractor_recognises_landmark_reference():
    geo = GeographicExtractor()
    res = geo.extract("The Likoni Floating Footbridge is collapsing")
    assert "Likoni Floating Footbridge" in res.landmarks


def test_extractor_uses_fallback_constituency():
    geo = GeographicExtractor()
    res = geo.extract("I have a complaint about water in my area", fallback_constituency="Nyali")
    assert res.constituency == "Nyali"
    assert res.fallback_used is True


def test_extractor_fallback_unknown_ignored():
    geo = GeographicExtractor()
    res = geo.extract("hello there", fallback_constituency="Atlantis")
    assert res.constituency is None
    assert res.fallback_used is False


def test_extractor_returns_empty_when_no_match():
    geo = GeographicExtractor()
    res = geo.extract("lorem ipsum dolor sit amet")
    assert res.constituency is None
    assert res.facilities == []
    assert res.landmarks == []
    assert res.roads == []
    assert res.confidence == 0.0


def test_extractor_does_not_overlap_known_constituency_as_substring():
    """'Mvita' should match Mvita, not e.g. a road starting with Mvita."""
    geo = GeographicExtractor()
    res = geo.extract("The Mvita market is on fire")
    assert "Mvita" == res.constituency


def test_extractor_recognises_ward():
    geo = GeographicExtractor()
    res = geo.extract("Pile of garbage in Kongowea")
    assert res.ward == "Kongowea"


def test_extractor_confidence_grows_with_multi_signal():
    geo = GeographicExtractor()
    sparse = geo.extract("Something is wrong in Likoni")
    rich = geo.extract(
        "Likoni constituency: Likoni Floating Footbridge is collapsing"
    )
    assert rich.confidence > sparse.confidence


def test_extractor_recognises_nyali_bridge_facility():
    geo = GeographicExtractor()
    res = geo.extract("Nyali Bridge has a problem")
    assert res.constituency in ("Nyali",)
    # The road/facility bag should pick up the landmark.
    assert any("Nyali" in x for x in res.landmarks + res.facilities + res.roads)


def test_to_dict_has_expected_keys():
    geo = GeographicExtractor()
    res = geo.extract("Potholes in Likoni")
    d = res.to_dict()
    for key in (
        "county",
        "constituency",
        "ward",
        "landmarks",
        "roads",
        "facilities",
        "fallback_used",
        "confidence",
        "matched_terms",
    ):
        assert key in d


def test_counties_constant_contains_mombasa():
    assert "Mombasa" in COUNTIES


def test_constituencies_constant_has_six_entries():
    assert len(CONSTITUENCIES) == 6
    for required in ("Likoni", "Mvita", "Nyali", "Kisauni", "Changamwe", "Jomvu"):
        assert required in CONSTITUENCIES
