"""Pydantic schemas for the Sprint 6 AI pipeline APIs."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class PipelineRequest(BaseModel):
    """Input payload for /api/v1/pipeline/run."""

    text: str = Field(..., min_length=1, max_length=4000, description="Raw citizen submission.")
    constituency: Optional[str] = Field(
        None,
        max_length=100,
        description="Optional constituency context (e.g. from the citizen's profile).",
    )
    include_trend: bool = Field(
        False,
        description="If true, attach a fresh trend-detection snapshot to the result.",
    )


class ClassificationResponse(BaseModel):
    category: str
    confidence: float
    matched_keywords: List[str] = []
    scores: Dict[str, float] = {}


class DuplicateMatchResponse(BaseModel):
    submission_id: int
    similarity: float
    token_jaccard: float
    trigram_jaccard: float
    raw_content: str
    constituency: Optional[str] = None
    submitted_at: Optional[str] = None


class DuplicateDetectionResponse(BaseModel):
    is_duplicate: bool
    best_match_id: Optional[int]
    best_similarity: float
    threshold: float
    matches: List[DuplicateMatchResponse] = []


class PriorityResponse(BaseModel):
    level: str
    score: float
    category: Optional[str] = None
    signals: Dict[str, float] = {}
    rationale: List[str] = []


class GeographyResponse(BaseModel):
    county: Optional[str] = None
    constituency: Optional[str] = None
    ward: Optional[str] = None
    landmarks: List[str] = []
    roads: List[str] = []
    facilities: List[str] = []
    fallback_used: bool = False
    confidence: float = 0.0
    matched_terms: List[str] = []


class TopicTagResponse(BaseModel):
    tag: str
    score: float
    matched_triggers: List[str] = []


class TopicsResponse(BaseModel):
    tags: List[TopicTagResponse] = []
    top_tag: Optional[str] = None


class PipelineResponse(BaseModel):
    """Top-level response payload for /api/v1/pipeline/run."""

    text: str
    classification: ClassificationResponse
    duplicate_detection: DuplicateDetectionResponse
    priority: PriorityResponse
    geography: GeographyResponse
    topics: TopicsResponse
    trend: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Liveness response for /api/v1/pipeline/health."""

    status: str = "ok"
    pipeline_version: str = "sprint-6"


__all__ = [
    "PipelineRequest",
    "ClassificationResponse",
    "DuplicateMatchResponse",
    "DuplicateDetectionResponse",
    "PriorityResponse",
    "GeographyResponse",
    "TopicTagResponse",
    "TopicsResponse",
    "PipelineResponse",
    "HealthResponse",
]
