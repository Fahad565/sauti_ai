"""Retrieval Service for SQL-backed RAG in Sauti AI.

Searches infrastructure, projects, previous submissions, and issues
using keyword and SQL filter queries with entity-aware relevance scoring.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.domain import Infrastructure, Issue, Project, Submission

KNOWN_CONSTITUENCIES = ["Likoni", "Mvita", "Nyali", "Kisauni", "Changamwe", "Jomvu"]

STOP_WORDS = {
    "is", "there", "a", "an", "the", "in", "of", "for", "and", "or", "to", "with",
    "on", "at", "are", "what", "where", "when", "how", "which", "who", "why",
    "can", "you", "tell", "me", "about", "any", "some", "please"
}


def extract_constituency(text: str) -> Optional[str]:
    """Extract known constituency name from text if present."""
    if not text:
        return None
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    words = cleaned.split()
    for name in KNOWN_CONSTITUENCIES:
        if name.lower() in words or name.lower() in cleaned:
            return name
    return None


def clean_keywords(text: str) -> List[str]:
    """Strip punctuation, stop words, and tokenize query text."""
    if not text:
        return []
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    tokens = [w.strip() for w in cleaned.split()]
    return [w for w in tokens if len(w) > 1 and w not in STOP_WORDS]


class RetrievalService:
    """Service handling structured SQL search and relevance scoring."""

    def __init__(self, db: Session):
        self.db = db

    def search_infrastructure(
        self,
        query: str,
        constituency: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search infrastructure assets by keyword and optional constituency."""
        target_constituency = constituency or extract_constituency(query)
        db_query = self.db.query(Infrastructure)

        if target_constituency and target_constituency.strip():
            db_query = db_query.filter(
                Infrastructure.constituency.ilike(f"%{target_constituency.strip()}%")
            )

        keywords = clean_keywords(query)
        search_kw = [k for k in keywords if k.lower() != (target_constituency or "").lower()]

        if search_kw:
            conditions = []
            for kw in search_kw:
                term = f"%{kw}%"
                conditions.append(Infrastructure.name.ilike(term))
                conditions.append(Infrastructure.type.ilike(term))
                conditions.append(Infrastructure.location.ilike(term))
                conditions.append(Infrastructure.capacity_details.ilike(term))
            db_query = db_query.filter(or_(*conditions))

        results = db_query.all()

        # Fall back to all constituencies if targeted filter returned zero results
        if not results and target_constituency and search_kw:
            fallback_query = self.db.query(Infrastructure)
            conditions = []
            for kw in search_kw:
                term = f"%{kw}%"
                conditions.append(Infrastructure.name.ilike(term))
                conditions.append(Infrastructure.type.ilike(term))
                conditions.append(Infrastructure.location.ilike(term))
            results = fallback_query.filter(or_(*conditions)).all()

        formatted = []
        for item in results:
            score = self._compute_relevance_score(
                query=query,
                name=item.name,
                category=item.type,
                location_desc=f"{item.location or ''} {item.capacity_details or ''}",
                item_constituency=item.constituency,
                target_constituency=target_constituency,
            )
            formatted.append({
                "id": item.id,
                "name": item.name,
                "type": item.type,
                "constituency": item.constituency,
                "location": item.location,
                "status": item.status,
                "capacity_details": item.capacity_details,
                "relevance_score": score,
            })

        sorted_results = sorted(formatted, key=lambda x: x["relevance_score"], reverse=True)
        return sorted_results[:limit]

    def search_projects(
        self,
        query: str,
        constituency: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search projects by keyword and optional constituency."""
        target_constituency = constituency or extract_constituency(query)
        db_query = self.db.query(Project)

        if target_constituency and target_constituency.strip():
            db_query = db_query.filter(
                Project.constituency.ilike(f"%{target_constituency.strip()}%")
            )

        keywords = clean_keywords(query)
        search_kw = [k for k in keywords if k.lower() != (target_constituency or "").lower()]

        if search_kw:
            conditions = []
            for kw in search_kw:
                term = f"%{kw}%"
                conditions.append(Project.name.ilike(term))
                conditions.append(Project.type.ilike(term))
                conditions.append(Project.description.ilike(term))
                conditions.append(Project.status.ilike(term))
            db_query = db_query.filter(or_(*conditions))

        results = db_query.all()

        if not results and target_constituency and search_kw:
            fallback_query = self.db.query(Project)
            conditions = []
            for kw in search_kw:
                term = f"%{kw}%"
                conditions.append(Project.name.ilike(term))
                conditions.append(Project.type.ilike(term))
                conditions.append(Project.description.ilike(term))
            results = fallback_query.filter(or_(*conditions)).all()

        formatted = []
        for item in results:
            score = self._compute_relevance_score(
                query=query,
                name=item.name,
                category=item.type,
                location_desc=item.description or "",
                item_constituency=item.constituency,
                target_constituency=target_constituency,
            )
            formatted.append({
                "id": item.id,
                "name": item.name,
                "type": item.type,
                "constituency": item.constituency,
                "status": item.status,
                "budget": item.budget,
                "description": item.description,
                "start_date": item.start_date,
                "target_completion_date": item.target_completion_date,
                "relevance_score": score,
            })

        sorted_results = sorted(formatted, key=lambda x: x["relevance_score"], reverse=True)
        return sorted_results[:limit]

    def search_submissions(
        self,
        query: str,
        constituency: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search previous submissions for duplicate/historical discovery."""
        target_constituency = constituency or extract_constituency(query)
        db_query = self.db.query(Submission)

        if target_constituency and target_constituency.strip():
            db_query = db_query.filter(
                Submission.constituency.ilike(f"%{target_constituency.strip()}%")
            )

        keywords = clean_keywords(query)
        search_kw = [k for k in keywords if k.lower() != (target_constituency or "").lower()]

        if search_kw:
            conditions = []
            for kw in search_kw:
                term = f"%{kw}%"
                conditions.append(Submission.raw_content.ilike(term))
                conditions.append(Submission.ward.ilike(term))
            db_query = db_query.filter(or_(*conditions))

        results = db_query.all()

        formatted = []
        for item in results:
            score = self._compute_relevance_score(
                query=query,
                name=item.raw_content[:50],
                category=item.ward or "",
                location_desc=item.raw_content,
                item_constituency=item.constituency,
                target_constituency=target_constituency,
            )
            formatted.append({
                "id": item.id,
                "raw_content": item.raw_content,
                "constituency": item.constituency,
                "ward": item.ward,
                "status": item.status,
                "submitted_at": item.submitted_at.isoformat() if item.submitted_at else None,
                "relevance_score": score,
            })

        sorted_results = sorted(formatted, key=lambda x: x["relevance_score"], reverse=True)
        return sorted_results[:limit]

    def search_issues(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search issues extracted from submissions."""
        db_query = self.db.query(Issue)

        if category and category.strip():
            db_query = db_query.filter(
                Issue.category.ilike(f"%{category.strip()}%")
            )

        keywords = clean_keywords(query)
        if keywords:
            conditions = []
            for kw in keywords:
                term = f"%{kw}%"
                conditions.append(Issue.title.ilike(term))
                conditions.append(Issue.category.ilike(term))
                conditions.append(Issue.severity.ilike(term))
            db_query = db_query.filter(or_(*conditions))

        results = db_query.all()

        formatted = []
        for item in results:
            score = self._compute_relevance_score(
                query=query,
                name=item.title,
                category=item.category,
                location_desc=item.severity,
                item_constituency=None,
                target_constituency=None,
            )
            formatted.append({
                "id": item.id,
                "title": item.title,
                "category": item.category,
                "severity": item.severity,
                "status": item.status,
                "relevance_score": score,
            })

        sorted_results = sorted(formatted, key=lambda x: x["relevance_score"], reverse=True)
        return sorted_results[:limit]

    def search_all(
        self,
        query: str,
        constituency: Optional[str] = None,
        limit: int = 5,
    ) -> Dict[str, Any]:
        """Perform unified multi-entity retrieval across infrastructure, projects, submissions, and issues."""
        target_constituency = constituency or extract_constituency(query)

        infra = self.search_infrastructure(query, target_constituency, limit=limit)
        projects = self.search_projects(query, target_constituency, limit=limit)
        submissions = self.search_submissions(query, target_constituency, limit=limit)
        issues = self.search_issues(query, limit=limit)

        total = len(infra) + len(projects) + len(submissions) + len(issues)

        return {
            "query": query,
            "constituency": target_constituency,
            "infrastructure": infra,
            "projects": projects,
            "submissions": submissions,
            "issues": issues,
            "total_matches": total,
        }

    def _compute_relevance_score(
        self,
        query: str,
        name: str,
        category: str,
        location_desc: str,
        item_constituency: Optional[str] = None,
        target_constituency: Optional[str] = None,
    ) -> float:
        """Compute weighted relevance score for ranking."""
        keywords = clean_keywords(query)
        score = 0.0

        # Constituency boost / penalty
        if target_constituency and item_constituency:
            if item_constituency.lower().strip() == target_constituency.lower().strip():
                score += 5.0
            else:
                score -= 2.0

        name_lower = name.lower() if name else ""
        cat_lower = category.lower() if category else ""
        desc_lower = location_desc.lower() if location_desc else ""

        for kw in keywords:
            if kw.lower() == (target_constituency or "").lower():
                continue
            if kw in name_lower:
                score += 4.0
            elif kw in cat_lower:
                score += 2.0
            elif kw in desc_lower:
                score += 1.0

        return round(max(0.0, score), 2)
