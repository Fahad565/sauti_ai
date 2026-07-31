"""Tests for the Sprint 7 MP Dashboard API and static SPA mount."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


# --------------------------------------------------------------------------- #
# SPA mount
# --------------------------------------------------------------------------- #


def test_dashboard_index_html_is_served() -> None:
    """GET /dashboard/index.html returns the SPA shell."""
    response = client.get("/dashboard/index.html")
    assert response.status_code == 200
    assert "Sauti AI" in response.text
    assert "MP Dashboard" in response.text


def test_dashboard_assets_are_served() -> None:
    """Static assets under /dashboard/assets/ are reachable."""
    for asset in ("app.js", "styles.css", "api.js", "ui.js", "overview.js"):
        r = client.get(f"/dashboard/assets/{asset}")
        assert r.status_code == 200, f"{asset} returned {r.status_code}"
        assert len(r.content) > 0


def test_dashboard_index_html_exists_on_disk() -> None:
    """The static folder matches what the SPA mount points at."""
    static_dir = Path(__file__).resolve().parents[1] / "app" / "static" / "dashboard"
    assert (static_dir / "index.html").is_file()
    assert (static_dir / "assets" / "app.js").is_file()
    assert (static_dir / "assets" / "styles.css").is_file()


# --------------------------------------------------------------------------- #
# /api/v1/dashboard/overview
# --------------------------------------------------------------------------- #


def test_overview_returns_cards_and_breakdowns() -> None:
    response = client.get("/api/v1/dashboard/overview")
    assert response.status_code == 200
    data = response.json()
    assert "cards" in data
    cards = data["cards"]
    # All KPI keys are present
    for key in (
        "citizen_reports",
        "open_issues",
        "total_projects",
        "total_infrastructure",
        "critical_issues",
        "todays_reports",
        "total_citizens",
    ):
        assert key in cards
        assert isinstance(cards[key], int)
    # Each breakdown is a list of {label, count}
    for key in ("by_constituency", "by_category", "by_priority", "top_topics", "trend"):
        assert key in data
        assert isinstance(data[key], list)


def test_overview_includes_all_known_constituencies() -> None:
    """All 6 known constituencies are present in the chart data, even if zero-count."""
    data = client.get("/api/v1/dashboard/overview").json()
    consts = {row["constituency"] for row in data["by_constituency"]}
    for c in ("Likoni", "Mvita", "Nyali", "Kisauni", "Changamwe", "Jomvu"):
        assert c in consts


def test_overview_filters_by_constituency() -> None:
    """GET /overview?constituency=Likoni filters cards by constituency."""
    res = client.get("/api/v1/dashboard/overview?constituency=Likoni")
    assert res.status_code == 200
    data = res.json()
    assert data["constituency"] == "Likoni"
    assert "cards" in data
    assert isinstance(data["cards"]["citizen_reports"], int)


def test_overview_trend_has_eight_weeks() -> None:
    data = client.get("/api/v1/dashboard/overview").json()
    assert len(data["trend"]) == 8
    for row in data["trend"]:
        assert "week" in row and "count" in row


# --------------------------------------------------------------------------- #
# /api/v1/dashboard/issues
# --------------------------------------------------------------------------- #


def test_issues_returns_items_and_facets() -> None:
    response = client.get("/api/v1/dashboard/issues")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data and "facets" in data
    for key in ("constituencies", "categories", "severities"):
        assert key in data["facets"]


def test_issues_filters_by_constituency() -> None:
    all_data = client.get("/api/v1/dashboard/issues?limit=500").json()
    target = None
    for row in all_data["items"]:
        if row["constituency"] and row["constituency"] != "Unknown":
            target = row["constituency"]
            break
    if target is None:
        return  # No data — nothing to assert.
    filtered = client.get(f"/api/v1/dashboard/issues?constituency={target}&limit=500").json()
    for item in filtered["items"]:
        assert item["constituency"] == target


def test_issues_filters_by_category() -> None:
    all_data = client.get("/api/v1/dashboard/issues?limit=500").json()
    if not all_data["items"]:
        return
    target = all_data["items"][0]["category"]
    filtered = client.get(f"/api/v1/dashboard/issues?category={target}&limit=500").json()
    for item in filtered["items"]:
        assert item["category"] == target


# --------------------------------------------------------------------------- #
# /api/v1/dashboard/infrastructure/summary + /api/v1/dashboard/projects/summary
# --------------------------------------------------------------------------- #


def test_infrastructure_summary_has_types() -> None:
    response = client.get("/api/v1/dashboard/infrastructure/summary")
    assert response.status_code == 200
    data = response.json()
    assert "by_type" in data and "by_constituency" in data
    if data["by_type"]:
        first = data["by_type"][0]
        assert "type" in first and "count" in first
        assert first["count"] > 0


def test_projects_summary_has_budget_total() -> None:
    response = client.get("/api/v1/dashboard/projects/summary")
    assert response.status_code == 200
    data = response.json()
    assert "by_status" in data
    assert "by_constituency" in data
    assert "budget_total" in data
    assert data["budget_total"] >= 0


# --------------------------------------------------------------------------- #
# /api/v1/dashboard/activity
# --------------------------------------------------------------------------- #


def test_activity_returns_recent_entries() -> None:
    response = client.get("/api/v1/dashboard/activity?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    for item in data["items"]:
        assert "kind" in item
        assert "timestamp" in item


# --------------------------------------------------------------------------- #
# /api/v1/dashboard/pipeline/preview
# --------------------------------------------------------------------------- #


def test_pipeline_preview_returns_all_stages() -> None:
    response = client.get(
        "/api/v1/dashboard/pipeline/preview?message=Is%20there%20a%20hospital%20in%20Likoni%3F"
    )
    assert response.status_code == 200
    data = response.json()
    stages = [s["stage"] for s in data["stages"]]
    assert stages == ["intake", "classify", "retrieval", "context", "analyze"]
    classify_stage = data["stages"][1]
    assert "intent" in classify_stage["output"]
    assert "confidence" in classify_stage["output"]
    retrieval_stage = data["stages"][2]
    assert "total_matches" in retrieval_stage["output"]
    assert "top_results" in retrieval_stage["output"]


def test_pipeline_preview_hospital_in_likoni_finds_hospital() -> None:
    response = client.get(
        "/api/v1/dashboard/pipeline/preview?message=Is%20there%20a%20hospital%20in%20Likoni%3F"
    )
    data = response.json()
    retrieval = data["stages"][2]["output"]
    assert retrieval["total_matches"] >= 1
    names = [r["name"].lower() for r in retrieval["top_results"]]
    assert any("hospital" in n for n in names)


def test_pipeline_preview_classifies_complaint() -> None:
    response = client.get(
        "/api/v1/dashboard/pipeline/preview",
        params={
            "message": "the road towards nyali from buxton is very poor with potholes",
        },
    )
    data = response.json()
    classify = data["stages"][1]["output"]
    assert classify["intent"] == "complaint"
    assert classify["confidence"] > 0.5
    assert "pothole" in (classify.get("keywords_matched") or [])


def test_pipeline_preview_requires_message() -> None:
    response = client.get("/api/v1/dashboard/pipeline/preview")
    assert response.status_code == 422
