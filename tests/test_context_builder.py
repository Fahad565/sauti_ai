"""Tests for ContextBuilder service."""

from app.services.context_builder import ContextBuilder


def test_context_builder_formatting():
    builder = ContextBuilder(max_chars=1000)
    data = {
        "infrastructure": [
            {
                "name": "Likoni Level 4 Hospital",
                "type": "Hospital",
                "location": "Shelly Beach",
                "constituency": "Likoni",
                "status": "operational",
                "capacity_details": "200 beds",
            }
        ],
        "projects": [
            {
                "name": "Mvita Tarmac Road Upgrading",
                "type": "Roads",
                "status": "Ongoing",
                "budget": 50000000.0,
                "description": "Tarmacking major access roads.",
                "target_completion_date": "2026-12-31",
            }
        ],
        "submissions": [
            {
                "raw_content": "No water in Shelly Beach for 3 days.",
                "ward": "Timbwani",
                "status": "received",
            }
        ],
        "issues": [
            {
                "title": "Water Shortage in Shelly Beach",
                "category": "Water",
                "severity": "high",
                "status": "open",
            }
        ],
    }

    context = builder.build_context(data)
    assert "### Verified Infrastructure Assets" in context
    assert "Likoni Level 4 Hospital" in context
    assert "### Constituency Projects" in context
    assert "Mvita Tarmac Road Upgrading" in context
    assert "### Previous Citizen Reports & Submissions" in context
    assert "### Known Categorized Issues" in context


def test_context_builder_empty():
    builder = ContextBuilder()
    context = builder.build_context({})
    assert context == "No matching records found in constituency database."


def test_context_builder_truncation():
    builder = ContextBuilder(max_chars=50)
    data = {
        "infrastructure": [
            {
                "name": "Very Long Infrastructure Name That Exceeds Context Length Limit Easily",
                "type": "Hospital",
                "location": "Shelly Beach",
                "constituency": "Likoni",
                "status": "operational",
            }
        ]
    }
    context = builder.build_context(data)
    assert len(context) <= 50
    assert "[Context truncated]" in context
