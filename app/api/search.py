"""Search API endpoints exposing SQL-backed RAG retrieval results."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.retrieval import RetrievalService

router = APIRouter(prefix="/api/v1", tags=["search"])


@router.get("/search")
def unified_search(
    q: str = Query(..., min_length=1, description="Search query string"),
    constituency: Optional[str] = Query(None, description="Constituency filter"),
    limit: int = Query(5, ge=1, le=50, description="Max results per category"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Perform multi-entity search across infrastructure, projects, submissions, and issues."""
    retrieval_svc = RetrievalService(db)
    return retrieval_svc.search_all(query=q, constituency=constituency, limit=limit)


@router.get("/projects/search")
def search_projects(
    q: str = Query(..., min_length=1, description="Search query string"),
    constituency: Optional[str] = Query(None, description="Constituency filter"),
    limit: int = Query(10, ge=1, le=50, description="Max results"),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Search constituency projects by keyword and optional constituency."""
    retrieval_svc = RetrievalService(db)
    return retrieval_svc.search_projects(query=q, constituency=constituency, limit=limit)


@router.get("/infrastructure/search")
def search_infrastructure(
    q: str = Query(..., min_length=1, description="Search query string"),
    constituency: Optional[str] = Query(None, description="Constituency filter"),
    limit: int = Query(10, ge=1, le=50, description="Max results"),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Search infrastructure assets by keyword and optional constituency."""
    retrieval_svc = RetrievalService(db)
    return retrieval_svc.search_infrastructure(query=q, constituency=constituency, limit=limit)
