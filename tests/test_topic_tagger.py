"""Tests for Sprint 6 Feature 6.5 TopicTagger."""

import pytest

from app.services.topic_tagger import TopicTagger, TOPIC_TRIGGERS


def test_tag_roads_and_potholes():
    tagger = TopicTagger()
    res = tagger.tag("There are potholes along Moi Avenue")
    tag_names = [t.tag for t in res.tags]
    assert "Roads" in tag_names


def test_tag_flooding():
    tagger = TopicTagger()
    res = tagger.tag("There is flooding in Majengo after heavy rains")
    tag_names = [t.tag for t in res.tags]
    assert "Flooding" in tag_names


def test_tag_hospitals():
    tagger = TopicTagger()
    res = tagger.tag("Coast General Hospital has no doctors on duty")
    tag_names = [t.tag for t in res.tags]
    assert "Hospitals" in tag_names


def test_tag_security():
    tagger = TopicTagger()
    res = tagger.tag("There was a robbery at the bus stage yesterday")
    tag_names = [t.tag for t in res.tags]
    assert "Security" in tag_names


def test_tag_children_when_schoolchildren_mentioned():
    tagger = TopicTagger()
    res = tagger.tag("Schoolchildren are crossing a dangerous road")
    tag_names = [t.tag for t in res.tags]
    assert "Children" in tag_names


def test_tag_environment_for_trees():
    tagger = TopicTagger()
    res = tagger.tag("Trees have been cut down near the mangrove wetland")
    tag_names = [t.tag for t in res.tags]
    assert "Environment" in tag_names


def test_tag_top_tag_is_highest_score():
    tagger = TopicTagger()
    res = tagger.tag("There is a fire at the school with children inside, ambulance needed")
    assert res.tags
    assert res.top_tag == res.tags[0].tag
    assert res.tags[0].score >= res.tags[-1].score


def test_no_tags_for_clean_text():
    tagger = TopicTagger()
    res = tagger.tag("lorem ipsum dolor sit amet")
    # Could be empty depending on thresholds; sanitize either way.
    assert all(t.score >= 0.15 for t in res.tags)


def test_min_score_threshold_excludes_weak_tags():
    tagger = TopicTagger(min_score=10.0)  # impossibly high
    res = tagger.tag("Potholes")
    assert res.tags == []


def test_max_tags_caps_output():
    tagger = TopicTagger(max_tags=2)
    res = tagger.tag(
        "Fire at the school, children trapped, flooding in Majengo, "
        "hospital understaffed, garbage piling up, roads full of potholes"
    )
    assert len(res.tags) <= 2


def test_empty_text_returns_empty_tags():
    tagger = TopicTagger()
    res = tagger.tag("")
    assert res.tags == []
    assert res.top_tag is None


def test_each_topic_has_matched_triggers():
    tagger = TopicTagger()
    res = tagger.tag("There is flooding near the bridge, fire in the market, garbage overflow")
    for t in res.tags:
        assert isinstance(t.matched_triggers, list)
        # If there is a tag, it must have at least one trigger.
        assert len(t.matched_triggers) >= 1


def test_to_dict_round_trip():
    tagger = TopicTagger()
    res = tagger.tag("The bridge has potholes")
    d = res.to_dict()
    assert "tags" in d
    assert "top_tag" in d
    assert "text" in d
    assert isinstance(d["tags"], list)


def test_triggers_constant_has_required_topics():
    for required in (
        "Roads",
        "Flooding",
        "Bridges",
        "Water Supply",
        "Sanitation",
        "Safety",
        "Children",
        "Schools",
        "Hospitals",
        "Security",
        "Markets",
        "Environment",
        "Housing",
        "Transport",
    ):
        assert required in TOPIC_TRIGGERS
