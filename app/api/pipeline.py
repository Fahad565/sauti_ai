"""Sprint 6 AI pipeline REST endpoints.

Exposes three endpoints under ``/api/v1/pipeline``:

* ``POST /api/v1/pipeline/run``     - run the full 6-stage pipeline on a text.
* ``POST /api/v1/pipeline/classify`` - run only the civic classifier.
* ``GET  /api/v1/pipeline/health``   - liveness probe.

The endpoints accept plain JSON and return JSON, so they can be
called from the dashboard front-end, the webhook's background
task, or external civic-partner integrations.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.pipeline import (
    PipelineRequest,
    PipelineResponse,
    ClassificationResponse,
    DuplicateDetectionResponse,
    DuplicateMatchResponse,
    PriorityResponse,
    GeographyResponse,
    TopicsResponse,
    TopicTagResponse,
    HealthResponse,
)
from app.services.pipeline_orchestrator import PipelineOrchestrator
from app.services.civic_classifier import CivicClassifier
from app.services.duplicate_detector import DuplicateDetector
from app.services.priority_scorer import PriorityScorer
from app.services.geographic_extractor import GeographicExtractor
from app.services.topic_tagger import TopicTagger
from app.services.trend_detector import TrendDetector


router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])


# --- Response builders ----------------------------------------------------


def _classification_to_response(c) -> ClassificationResponse:
    return ClassificationResponse(
        category=c.category,
        confidence=c.confidence,
        matched_keywords=c.matched_keywords,
        scores=c.scores,
    )


def _duplicate_to_response(d) -> DuplicateDetectionResponse:
    return DuplicateDetectionResponse(
        is_duplicate=d.is_duplicate,
        best_match_id=d.best_match_id,
        best_similarity=d.best_similarity,
        threshold=d.threshold,
        matches=[
            DuplicateMatchResponse(
                submission_id=m.submission_id,
                similarity=m.similarity,
                token_jaccard=m.token_jaccard,
                trigram_jaccard=m.trigram_jaccard,
                raw_content=m.raw_content,
                constituency=m.constituency,
                submitted_at=m.submitted_at,
            )
            for m in d.matches
        ],
    )


def _priority_to_response(p) -> PriorityResponse:
    return PriorityResponse(
        level=p.level,
        score=p.score,
        category=p.category,
        signals=p.signals,
        rationale=p.rationale,
    )


def _geography_to_response(g) -> GeographyResponse:
    return GeographyResponse(
        county=g.county,
        constituency=g.constituency,
        ward=g.ward,
        landmarks=g.landmarks,
        roads=g.roads,
        facilities=g.facilities,
        fallback_used=g.fallback_used,
        confidence=g.confidence,
        matched_terms=g.matched_terms,
    )


def _topics_to_response(t) -> TopicsResponse:
    return TopicsResponse(
        tags=[
            TopicTagResponse(tag=tt.tag, score=tt.score, matched_triggers=tt.matched_triggers)
            for tt in t.tags
        ],
        top_tag=t.top_tag,
    )


# --- Endpoints -----------------------------------------------------------


@router.get("/health", response_model=HealthResponse, summary="Pipeline liveness probe")
def health() -> HealthResponse:
    """Return a static OK payload so an external caller can verify the
    pipeline router is wired in correctly."""
    return HealthResponse(status="ok", pipeline_version="sprint-6")


@router.post(
    "/run",
    response_model=PipelineResponse,
    summary="Run the full 6-stage AI pipeline on a submission",
)
def run_pipeline(
    payload: PipelineRequest,
    db: Session = Depends(get_db),
) -> PipelineResponse:
    """Execute every Sprint 6 pipeline stage on ``payload.text``.

    Order of execution:
    ``classification -> duplicate_detection -> priority -> geography -> topics -> trend``
    """
    try:
        orchestrator = PipelineOrchestrator(db, include_trend=payload.include_trend)
        result = orchestrator.run(
            payload.text,
            constituency=payload.constituency,
            include_trend=payload.include_trend,
        )
        return PipelineResponse(
            text=result.text,
            classification=_classification_to_response(result.classification),
            duplicate_detection=_duplicate_to_response(result.duplicate_detection),
            priority=_priority_to_response(result.priority),
            geography=_geography_to_response(result.geography),
            topics=_topics_to_response(result.topics),
            trend=result.trend,
        )
    except Exception as exc:  # noqa: BLE001 - convert to HTTP 500 cleanly
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"pipeline_run_failed: {exc.__class__.__name__}",
        )


@router.post(
    "/classify",
    response_model=ClassificationResponse,
    summary="Run only the civic classifier on a submission",
)
def run_classifier(
    payload: PipelineRequest,
    db: Session = Depends(get_db),  # noqa: ARG001 - kept for signature stability
) -> ClassificationResponse:
    """Run only Feature 6.1 (civic classification)."""
    return _classification_to_response(CivicClassifier().classify(payload.text))


@router.post(
    "/duplicates",
    response_model=DuplicateDetectionResponse,
    summary="Detect duplicate submissions",
)
def run_duplicate_detection(
    payload: PipelineRequest,
    db: Session = Depends(get_db),
) -> DuplicateDetectionResponse:
    """Run only Feature 6.2 (duplicate detection)."""
    detector = DuplicateDetector(db)
    return _duplicate_to_response(
        detector.detect(payload.text, constituency=payload.constituency)
    )


@router.post(
    "/priority",
    response_model=PriorityResponse,
    summary="Score submission severity",
)
def run_priority_score(
    payload: PipelineRequest,
    db: Session = Depends(get_db),  # noqa: ARG001
) -> PriorityResponse:
    """Run only Feature 6.3 (priority scoring)."""
    classifier = CivicClassifier().classify(payload.text)
    detector = DuplicateDetector(db)
    dup = detector.detect(payload.text, constituency=payload.constituency)
    priority = PriorityScorer().score(
        payload.text,
        category=classifier.category,
        duplicate_count=len(dup.matches),
    )
    return _priority_to_response(priority)


@router.post(
    "/geography",
    response_model=GeographyResponse,
    summary="Extract geographic references from a submission",
)
def run_geography(payload: PipelineRequest) -> GeographyResponse:
    """Run only Feature 6.4 (geographic extraction)."""
    return _geography_to_response(
        GeographicExtractor().extract(payload.text, fallback_constituency=payload.constituency)
    )


@router.post(
    "/topics",
    response_model=TopicsResponse,
    summary="Tag submission with topics",
)
def run_topics(payload: PipelineRequest) -> TopicsResponse:
    """Run only Feature 6.5 (topic tagging)."""
    return _topics_to_response(TopicTagger().tag(payload.text))


@router.get(
    "/trends",
    summary="Aggregate a recent-window trend report",
)
def run_trends(db: Session = Depends(get_db)) -> dict:
    """Run Feature 6.6 (trend detection) and return a JSON-ready dict."""
    return TrendDetector(db).detect().to_dict()
