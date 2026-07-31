"""Sprint 6 AI pipeline orchestrator.

Stitches the six Sprint 6 services together in a single call:

    1. Civic classification  → category
    2. Duplicate detection   → set of candidate matches
    3. Priority scoring      → severity level (Critical/High/Medium/Low)
    4. Geographic extraction → county, constituency, ward, landmarks...
    5. Topic tagging         → multi-label tags
    6. Trend detection       → (Optional) snapshot of recent activity

The orchestrator is intentionally a thin dispatcher: each stage has
its own service module and its own data class, this object just calls
them in order and merges the results.  It is the single entry point
the webhook, REST pipeline endpoints, and tests should use.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from app.services.civic_classifier import CivicClassifier, CivicClassification
from app.services.duplicate_detector import DuplicateDetector, DuplicateDetectionResult
from app.services.priority_scorer import PriorityScorer, PriorityScore
from app.services.geographic_extractor import GeographicExtractor, GeographicExtraction
from app.services.topic_tagger import TopicTagger, TopicTaggingResult
from app.services.trend_detector import TrendDetector


@dataclass
class PipelineResult:
    """Aggregate output of running the Sprint 6 pipeline on one input."""

    text: str
    classification: CivicClassification
    duplicate_detection: DuplicateDetectionResult
    priority: PriorityScore
    geography: GeographicExtraction
    topics: TopicTaggingResult
    trend: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "classification": self.classification.to_dict(),
            "duplicate_detection": self.duplicate_detection.to_dict(),
            "priority": self.priority.to_dict(),
            "geography": self.geography.to_dict(),
            "topics": self.topics.to_dict(),
            "trend": self.trend,
        }


class PipelineOrchestrator:
    """Run the full Sprint 6 AI pipeline on a citizen submission."""

    def __init__(
        self,
        db: Session,
        duplicate_threshold: float = 0.60,
        include_trend: bool = False,
    ) -> None:
        self.db = db
        self.civic_classifier = CivicClassifier()
        self.duplicate_detector = DuplicateDetector(db, threshold=duplicate_threshold)
        self.priority_scorer = PriorityScorer()
        self.geographic_extractor = GeographicExtractor()
        self.topic_tagger = TopicTagger()
        self.include_trend = include_trend
        self.trend_detector = TrendDetector(db) if include_trend else None

    def run(
        self,
        text: str,
        *,
        constituency: Optional[str] = None,
        include_trend: Optional[bool] = None,
    ) -> PipelineResult:
        """Execute the six stages in order and merge the result."""
        text = text or ""

        # 1. Civic classification
        classification = self.civic_classifier.classify(text)

        # 2. Duplicate detection (uses constituency fallback if known)
        dup_result = self.duplicate_detector.detect(
            text,
            constituency=constituency or classification.category and None,
        )

        # 3. Priority scoring (uses category + duplicate pressure)
        priority = self.priority_scorer.score(
            text,
            category=classification.category,
            duplicate_count=len(dup_result.matches),
        )

        # 4. Geographic extraction
        geography = self.geographic_extractor.extract(
            text,
            fallback_constituency=constituency,
        )

        # 5. Topic tagging
        topics = self.topic_tagger.tag(text)

        # 6. Trend detection (optional)
        trend_payload: Optional[Dict[str, Any]] = None
        want_trend = self.include_trend if include_trend is None else include_trend
        if want_trend and self.trend_detector is not None:
            trend_payload = self.trend_detector.detect().to_dict()

        return PipelineResult(
            text=text,
            classification=classification,
            duplicate_detection=dup_result,
            priority=priority,
            geography=geography,
            topics=topics,
            trend=trend_payload,
        )
