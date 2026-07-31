"""Dashboard analytics endpoints powering the Sprint 7 MP Dashboard SPA.

These endpoints aggregate data the existing CRUD endpoints already expose,
but in shapes the dashboard renders directly. They never mutate state and
are deliberately read-only so they can be called as often as the page
needs without contention on the database.

All responses are JSON. No auth (per the Sprint 7 spec: "No login.
No authentication. Just open the URL and see the intelligence.").
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.domain import (
    AgentAction,
    AISummary,
    Cluster,
    Infrastructure,
    Issue,
    Project,
    Submission,
    User,
)
from app.services.retrieval import KNOWN_CONSTITUENCIES


router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _percent(part: int, whole: int) -> float:
    if whole <= 0:
        return 0.0
    return round((part / whole) * 100.0, 1)


def _week_bucket_labels(n_weeks: int = 8) -> List[str]:
    """Return ISO date strings for the last n_weeks weeks (oldest first)."""
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=today.weekday())  # Monday
    labels: List[str] = []
    for i in range(n_weeks):
        week_start = start - timedelta(weeks=n_weeks - 1 - i)
        labels.append(week_start.isoformat())
    return labels


def _isoweek_key(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    iso = dt.date().isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


# --------------------------------------------------------------------------- #
# Overview
# --------------------------------------------------------------------------- #


@router.get("/overview", summary="Aggregated counts for dashboard Overview cards")
def overview(
    constituency: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Single-shot overview payload for the landing page.

    Returns:
        citizen_reports, open_issues, total_projects, total_infrastructure,
        critical_issues, todays_reports, counts by constituency, by
        category, by severity, top topics (truncated), and a trend
        series for the last 8 weeks.
    """
    # --- Base queries filtered by constituency if present ---
    sub_q = db.query(Submission)
    issue_q = db.query(Issue).join(Submission, Issue.submission_id == Submission.id)
    proj_q = db.query(Project)
    infra_q = db.query(Infrastructure)
    user_q = db.query(User)

    if constituency:
        sub_q = sub_q.filter(Submission.constituency == constituency)
        issue_q = issue_q.filter(Submission.constituency == constituency)
        proj_q = proj_q.filter(Project.constituency == constituency)
        infra_q = infra_q.filter(Infrastructure.constituency == constituency)
        user_q = user_q.filter(User.constituency == constituency)

    citizen_reports = sub_q.count()
    open_issues = issue_q.filter(Issue.status == "open").count()
    total_projects = proj_q.count()
    total_infrastructure = infra_q.count()
    critical_issues = issue_q.filter(Issue.severity.in_(["critical", "high"])).count()

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    todays_reports = sub_q.filter(Submission.submitted_at >= today_start).count()
    total_citizens = user_q.count()

    # --- Reports by constituency -------------------------------------------
    by_constituency_rows = (
        db.query(Submission.constituency, func.count(Submission.id))
        .group_by(Submission.constituency)
        .all()
    )
    by_constituency = [
        {"constituency": c or "Unknown", "count": int(n)}
        for c, n in by_constituency_rows
        if c
    ]
    present = {row["constituency"] for row in by_constituency}
    for c in KNOWN_CONSTITUENCIES:
        if c not in present:
            by_constituency.append({"constituency": c, "count": 0})
    by_constituency.sort(key=lambda r: r["count"], reverse=True)

    # --- Reports by category (using Issue table) --------------------------
    cat_query = db.query(Issue.category, func.count(Issue.id)).join(Submission, Issue.submission_id == Submission.id)
    if constituency:
        cat_query = cat_query.filter(Submission.constituency == constituency)
    by_category_rows = cat_query.group_by(Issue.category).all()
    by_category = [
        {"category": cat or "uncategorized", "count": int(n)}
        for cat, n in by_category_rows
    ]
    by_category.sort(key=lambda r: r["count"], reverse=True)

    # --- Reports by priority (severity) -----------------------------------
    sev_query = db.query(Issue.severity, func.count(Issue.id)).join(Submission, Issue.submission_id == Submission.id)
    if constituency:
        sev_query = sev_query.filter(Submission.constituency == constituency)
    by_priority_rows = sev_query.group_by(Issue.severity).all()
    by_priority = [
        {"severity": sev or "medium", "count": int(n)}
        for sev, n in by_priority_rows
    ]
    by_priority.sort(key=lambda r: r["count"], reverse=True)

    # --- Top topics (token n-grams of submission raw_content) --------------
    stop = {
        "the", "a", "an", "is", "are", "was", "were", "and", "or", "of", "to",
        "in", "on", "at", "for", "with", "we", "i", "you", "they", "it", "this",
        "that", "be", "been", "have", "has", "had", "do", "does", "did", "our",
        "us", "but", "not", "no", "yes", "from", "by", "as", "if", "so", "please",
    }
    counter: Counter[str] = Counter()
    for (text,) in sub_q.with_entities(Submission.raw_content).all():
        if not text:
            continue
        for token in text.lower().split():
            token = token.strip(".,!?;:'\"()[]{}")
            if len(token) < 4 or token in stop:
                continue
            counter[token] += 1
    top_topics = [{"topic": t, "count": int(c)} for t, c in counter.most_common(10)]

    # --- 8-week trend -----------------------------------------------------
    weeks = _week_bucket_labels(8)
    trend_counts: Dict[str, int] = {w: 0 for w in weeks}
    eight_weeks_ago = datetime.now(timezone.utc) - timedelta(weeks=8)
    for (submitted_at,) in sub_q.with_entities(Submission.submitted_at).filter(
        Submission.submitted_at >= eight_weeks_ago
    ).all():
        key = _isoweek_key(submitted_at)
        if key:
            year, week = key.split("-W")
            monday = datetime.strptime(f"{year}-W{week}-1", "%Y-W%W-%w").date()
            iso_monday = monday.isoformat()
            if iso_monday in trend_counts:
                trend_counts[iso_monday] += 1
    trend = [{"week": w, "count": trend_counts.get(w, 0)} for w in weeks]

    return {
        "constituency": constituency or "All",
        "cards": {
            "citizen_reports": int(citizen_reports),
            "open_issues": int(open_issues),
            "total_projects": int(total_projects),
            "total_infrastructure": int(total_infrastructure),
            "critical_issues": int(critical_issues),
            "todays_reports": int(todays_reports),
            "total_citizens": int(total_citizens),
        },
        "by_constituency": by_constituency,
        "by_category": by_category,
        "by_priority": by_priority,
        "top_topics": top_topics,
        "trend": trend,
    }


# --------------------------------------------------------------------------- #
# Issues Explorer
# --------------------------------------------------------------------------- #


@router.get("/issues", summary="Issues explorer feed with filters")
def issues(
    constituency: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Return joined Issue + Submission + User rows for the explorer."""
    query = (
        db.query(Issue, Submission, User)
        .join(Submission, Issue.submission_id == Submission.id)
        .join(User, Submission.user_id == User.id)
    )
    if constituency:
        query = query.filter(Submission.constituency == constituency)
    if category:
        query = query.filter(Issue.category == category)
    if severity:
        query = query.filter(Issue.severity == severity)
    rows = query.order_by(Issue.created_at.desc()).limit(limit).all()

    items: List[Dict[str, Any]] = []
    for issue, submission, user in rows:
        message_excerpt = (submission.raw_content or "")[:240]
        if topic and topic.lower() not in message_excerpt.lower():
            continue
        items.append(
            {
                "id": issue.id,
                "title": issue.title,
                "category": issue.category,
                "severity": issue.severity,
                "status": issue.status,
                "constituency": submission.constituency or "Unknown",
                "ward": submission.ward,
                "citizen_name": user.name,
                "citizen_phone": user.phone_number,
                "message": message_excerpt,
                "message_full": submission.raw_content,
                # prefer submission timestamp (always set by seed), fall back to issue auto-timestamp
                "created_at": (
                    submission.submitted_at.isoformat() if submission.submitted_at
                    else (issue.created_at.isoformat() if issue.created_at else None)
                ),
            }
        )

    # Aggregate facet counts (computed across the unfiltered, non-topic set
    # so the filter dropdowns remain stable as the user changes them).
    facet_query = (
        db.query(Issue, Submission).join(Submission, Issue.submission_id == Submission.id)
    )
    facets_rows = facet_query.all()
    constituencies: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    severities: Counter[str] = Counter()
    for issue, submission in facets_rows:
        if submission.constituency:
            constituencies[submission.constituency] += 1
        if issue.category:
            categories[issue.category] += 1
        if issue.severity:
            severities[issue.severity] += 1

    return {
        "items": items,
        "facets": {
            "constituencies": [{"value": k, "count": v} for k, v in constituencies.most_common()],
            "categories": [{"value": k, "count": v} for k, v in categories.most_common()],
            "severities": [{"value": k, "count": v} for k, v in severities.most_common()],
        },
    }


# --------------------------------------------------------------------------- #
# Infrastructure explorer aggregates
# --------------------------------------------------------------------------- #


@router.get("/infrastructure/summary", summary="Infrastructure counts per type and per constituency")
def infrastructure_summary(
    constituency: Optional[str] = Query(None),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    query = db.query(Infrastructure.type, Infrastructure.constituency, func.count(Infrastructure.id))
    if constituency:
        query = query.filter(Infrastructure.constituency == constituency)
    rows = query.group_by(Infrastructure.type, Infrastructure.constituency).all()
    by_type: Dict[str, int] = defaultdict(int)
    by_constituency: Dict[str, int] = defaultdict(int)
    for t, c, n in rows:
        if t:
            by_type[t] += int(n)
        if c:
            by_constituency[c] += int(n)
    return {
        "by_type": [{"type": k, "count": v} for k, v in sorted(by_type.items(), key=lambda r: r[1], reverse=True)],
        "by_constituency": [
            {"constituency": k, "count": v} for k, v in sorted(by_constituency.items(), key=lambda r: r[1], reverse=True)
        ],
    }


# --------------------------------------------------------------------------- #
# Projects explorer aggregates
# --------------------------------------------------------------------------- #


@router.get("/projects/summary", summary="Project counts by status and constituency")
def projects_summary(
    constituency: Optional[str] = Query(None),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    status_q = db.query(Project.status, func.count(Project.id))
    const_q = db.query(Project.constituency, func.count(Project.id))
    budget_q = db.query(func.coalesce(func.sum(Project.budget), 0.0))
    if constituency:
        status_q = status_q.filter(Project.constituency == constituency)
        const_q = const_q.filter(Project.constituency == constituency)
        budget_q = budget_q.filter(Project.constituency == constituency)

    status_rows = status_q.group_by(Project.status).all()
    constituency_rows = const_q.group_by(Project.constituency).all()
    budget_total = budget_q.scalar() or 0.0
    return {
        "by_status": [{"status": s or "Unknown", "count": int(n)} for s, n in status_rows],
        "by_constituency": [
            {"constituency": c or "Unknown", "count": int(n)} for c, n in constituency_rows
        ],
        "budget_total": float(budget_total),
    }


# --------------------------------------------------------------------------- #
# Live Activity feed
# --------------------------------------------------------------------------- #


@router.get("/activity", summary="Recent submissions, issues, agent actions, and AI summaries")
def activity(
    constituency: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Return a merged, time-ordered activity feed.

    Each entry has: ``kind`` (one of ``submission`` / ``issue`` / ``agent_action`` /
    ``ai_summary``), ``summary``, ``constituency`` (if known), and ``timestamp``.
    """
    entries: List[Dict[str, Any]] = []

    sub_q = db.query(Submission, User).join(User, Submission.user_id == User.id)
    if constituency:
        sub_q = sub_q.filter(Submission.constituency == constituency)
    submissions = sub_q.order_by(Submission.submitted_at.desc()).limit(limit).all()

    for s, u in submissions:
        entries.append(
            {
                "kind": "submission",
                "summary": (s.raw_content or "")[:160],
                "constituency": s.constituency,
                "citizen": u.name or u.phone_number,
                "timestamp": s.submitted_at.isoformat() if s.submitted_at else None,
            }
        )

    issue_q = db.query(Issue).join(Submission, Issue.submission_id == Submission.id)
    if constituency:
        issue_q = issue_q.filter(Submission.constituency == constituency)
    issues = issue_q.order_by(Issue.created_at.desc()).limit(limit).all()

    for i in issues:
        entries.append(
            {
                "kind": "issue",
                "summary": f"{i.title} ({i.severity}/{i.status})",
                "constituency": i.submission.constituency if i.submission else None,
                "citizen": None,
                "timestamp": i.created_at.isoformat() if i.created_at else None,
            }
        )

    actions = (
        db.query(AgentAction).order_by(AgentAction.created_at.desc()).limit(limit).all()
    )
    for a in actions:
        entries.append(
            {
                "kind": "agent_action",
                "summary": f"{a.action_type}: {(a.reasoning_notes or '')[:120]}",
                "constituency": None,
                "citizen": None,
                "timestamp": a.created_at.isoformat() if a.created_at else None,
            }
        )

    summaries = (
        db.query(AISummary).order_by(AISummary.created_at.desc()).limit(limit).all()
    )
    for s in summaries:
        entries.append(
            {
                "kind": "ai_summary",
                "summary": (s.summary_text or "")[:160],
                "constituency": None,
                "citizen": None,
                "intent": s.extracted_intent,
                "timestamp": s.created_at.isoformat() if s.created_at else None,
            }
        )

    entries.sort(key=lambda e: e.get("timestamp") or "", reverse=True)
    return {"items": entries[:limit]}


# --------------------------------------------------------------------------- #
# AI Pipeline simulator
# --------------------------------------------------------------------------- #


@router.get("/pipeline/preview", summary="Simulate the AI pipeline for a hypothetical citizen message")
def pipeline_preview(
    message: str = Query(..., min_length=1, description="Hypothetical citizen message"),
    constituency: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Return a stage-by-stage preview of how the LangGraph pipeline would process
    ``message`` right now, without actually invoking the LLM.

    This is what powers the AI Pipeline Visualizer on the dashboard: it shows
    the user the same intermediate state the agent would see (classification,
    retrieval, context assembly) so judges can see _how_ the answer is grounded.
    """
    from app.services.classifier import IntentClassifier
    from app.services.context_builder import ContextBuilder
    from app.services.retrieval import RetrievalService, extract_constituency

    # Stage 1: Intake
    intake = {
        "stage": "intake",
        "label": "Citizen message",
        "input": message,
        "output": {"length": len(message)},
        "duration_ms": 0,
    }

    # Stage 2: Classify
    import time

    t = time.perf_counter()
    classifier = IntentClassifier()
    classification = classifier.classify(message)
    detected_constituency = constituency or extract_constituency(message)
    classify_stage = {
        "stage": "classify",
        "label": "Classifier",
        "input": message,
        "output": {
            "intent": classification["intent"],
            "confidence": classification["confidence"],
            "keywords_matched": classification.get("keywords_matched", []),
        },
        "detected_constituency": detected_constituency,
        "duration_ms": int((time.perf_counter() - t) * 1000),
    }

    # Stage 3: Retrieval
    t = time.perf_counter()
    retrieval = RetrievalService(db)
    results = retrieval.search_all(query=message, constituency=detected_constituency, limit=5)
    retrieval_stage = {
        "stage": "retrieval",
        "label": "SQL Retrieval",
        "input": {"query": message, "constituency": detected_constituency},
        "output": {
            "total_matches": results.get("total_matches", 0),
            "infrastructure_count": len(results.get("infrastructure", [])),
            "projects_count": len(results.get("projects", [])),
            "submissions_count": len(results.get("submissions", [])),
            "issues_count": len(results.get("issues", [])),
            "top_results": [
                {
                    "name": (r.get("name") or r.get("title") or ""),
                    "type": r.get("type") or r.get("category") or "submission",
                    "constituency": r.get("constituency"),
                    "relevance_score": r.get("relevance_score", 0.0),
                }
                for r in (
                    results.get("infrastructure", [])
                    + results.get("projects", [])
                    + results.get("submissions", [])
                )[:5]
            ],
        },
        "duration_ms": int((time.perf_counter() - t) * 1000),
    }

    # Stage 4: Context assembly
    t = time.perf_counter()
    builder = ContextBuilder(max_chars=4000)
    context = builder.build_context(results)
    context_stage = {
        "stage": "context",
        "label": "Context assembly",
        "input": retrieval_stage["output"],
        "output": {"context_chars": len(context), "preview": context[:400]},
        "duration_ms": int((time.perf_counter() - t) * 1000),
    }

    # Stage 5: LLM (gated) — we never call the real LLM here, but we describe it.
    llm_stage = {
        "stage": "analyze",
        "label": "Gemma 4 LLM",
        "input": {
            "system_prompt_chars": 0,
            "rag_prompt_chars": len(context) + len(message) + 256,
            "intent": classification["intent"],
            "constituency": detected_constituency or "General",
        },
        "output": "(live LLM call disabled in dashboard preview)",
        "duration_ms": None,
    }

    return {
        "stages": [intake, classify_stage, retrieval_stage, context_stage, llm_stage],
        "constituency": detected_constituency,
    }
