"""Tests for IntentClassifier service."""

from app.services.classifier import IntentClassifier


def test_classify_infrastructure_lookup():
    classifier = IntentClassifier()
    res = classifier.classify("Where is Likoni level 4 hospital located?")
    assert res["intent"] == "infrastructure_lookup"
    assert res["confidence"] >= 0.5


def test_classify_project_lookup():
    classifier = IntentClassifier()
    res = classifier.classify("What is the status of the tarmac road project?")
    assert res["intent"] == "project_lookup"
    assert res["confidence"] >= 0.5


def test_classify_complaint():
    classifier = IntentClassifier()
    res = classifier.classify("The water pipe is broken and leaking everywhere!")
    assert res["intent"] == "complaint"
    assert res["confidence"] >= 0.5


def test_classify_status_update():
    classifier = IntentClassifier()
    res = classifier.classify("When will construction finish?")
    assert res["intent"] == "status_update"
    assert res["confidence"] >= 0.5


def test_classify_general_question():
    classifier = IntentClassifier()
    res = classifier.classify("Hello Sauti AI")
    assert res["intent"] == "general_question"
    assert res["confidence"] == 0.6
