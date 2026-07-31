"""Duplicate detection service for Sprint 6 Feature 6.2.

Identifies whether a new citizen submission is a duplicate of an
existing one. Two layers of similarity:

1. Token-set Jaccard similarity.
2. Trigram-set Jaccard similarity (catches word-order variants).

A combined score >= ``DEFAULT_THRESHOLD`` (0.60) marks the submission
as a duplicate. The service can optionally restrict the search to a
target constituency to avoid matching complaints in Mombasa CBD
against ones in Likoni.

References: DECISION-0018.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Any, Optional, Sequence

from sqlalchemy.orm import Session

from app.models.domain import Submission


DEFAULT_THRESHOLD = 0.60
TIME_WINDOW_DAYS = 30  # Only look back this far when scanning history


# Stop words stripped before tokenisation (kept in sync with retrieval.py).
STOP_WORDS = {
    "is", "there", "a", "an", "the", "in", "of", "for", "and", "or", "to",
    "with", "on", "at", "are", "what", "where", "when", "how", "which",
    "who", "why", "can", "you", "tell", "me", "about", "any", "some",
    "please", "this", "that", "these", "those", "it", "its", "i",
    "we", "they", "be", "been", "has", "have", "had", "do", "does",
}


@dataclass
class DuplicateMatch:
    """A candidate duplicate match returned by the service."""

    submission_id: int
    similarity: float
    token_jaccard: float
    trigram_jaccard: float
    raw_content: str
    constituency: Optional[str] = None
    submitted_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DuplicateDetectionResult:
    """Aggregate result of a duplicate-detection run."""

    is_duplicate: bool
    best_match_id: Optional[int]
    best_similarity: float
    threshold: float
    matches: List[DuplicateMatch] = field(default_factory=list)
    text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        out = asdict(self)
        out["matches"] = [m.to_dict() for m in self.matches]
        return out


def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return [t.strip() for t in cleaned.split() if t.strip() and t.strip() not in STOP_WORDS]


def _trigrams(text: str) -> List[str]:
    """Generate character-level trigrams for trigram Jaccard."""
    normalized = re.sub(r"\s+", " ", (text or "").lower().strip())
    if len(normalized) < 3:
        return [normalized] if normalized else []
    return [normalized[i : i + 3] for i in range(len(normalized) - 2)]


def _jaccard(a: Iterable, b: Iterable) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 0.0
    if not sa or not sb:
        return 0.0
    intersection = sa & sb
    union = sa | sb
    return len(intersection) / len(union)


class DuplicateDetector:
    """Detect duplicate submissions against the historical record.

    Usage::

        detector = DuplicateDetector(db)
        result = detector.detect(
            "There are potholes on the Likoni road",
            constituency="Likoni",
        )
        if result.is_duplicate:
            ...
    """

    def __init__(
        self,
        db: Session,
        threshold: float = DEFAULT_THRESHOLD,
        time_window_days: int = TIME_WINDOW_DAYS,
    ) -> None:
        self.db = db
        self.threshold = threshold
        self.time_window_days = time_window_days

    def _candidate_submissions(
        self,
        constituency: Optional[str],
    ) -> Sequence[Submission]:
        query = self.db.query(Submission)
        if constituency:
            query = query.filter(Submission.constituency.ilike(f"%{constituency}%"))
        if self.time_window_days and self.time_window_days > 0:
            cutoff = datetime.now(timezone.utc) - timedelta(days=self.time_window_days)
            query = query.filter(Submission.submitted_at >= cutoff)
        return query.order_by(Submission.submitted_at.desc()).limit(500).all()

    def detect(
        self,
        text: str,
        constituency: Optional[str] = None,
        *,
        candidates: Optional[Sequence[Submission]] = None,
    ) -> DuplicateDetectionResult:
        """Detect whether ``text`` duplicates a prior submission."""
        # Empty submissions cannot be duplicates; skip work.
        if not text or not text.strip():
            return DuplicateDetectionResult(
                is_duplicate=False,
                best_match_id=None,
                best_similarity=0.0,
                threshold=self.threshold,
                matches=[],
                text=text or "",
            )

        tokens = _tokenize(text)
        trigrams = _trigrams(text)

        if not tokens:
            return DuplicateDetectionResult(
                is_duplicate=False,
                best_match_id=None,
                best_similarity=0.0,
                threshold=self.threshold,
                matches=[],
                text=text,
            )

        cand_list = (
            list(candidates)
            if candidates is not None
            else list(self._candidate_submissions(constituency))
        )

        matches: List[DuplicateMatch] = []

        for sub in cand_list:
            cand_tokens = _tokenize(sub.raw_content)
            cand_trigrams = _trigrams(sub.raw_content)

            tj = _jaccard(tokens, cand_tokens)
            tg = _jaccard(trigrams, cand_trigrams)
            sim = round(0.5 * tj + 0.5 * tg, 4)

            if sim >= self.threshold:
                matches.append(
                    DuplicateMatch(
                        submission_id=sub.id,
                        similarity=sim,
                        token_jaccard=round(tj, 4),
                        trigram_jaccard=round(tg, 4),
                        raw_content=sub.raw_content,
                        constituency=sub.constituency,
                        submitted_at=sub.submitted_at.isoformat() if sub.submitted_at else None,
                    )
                )

        matches.sort(key=lambda m: m.similarity, reverse=True)

        best = matches[0] if matches else None
        return DuplicateDetectionResult(
            is_duplicate=best is not None,
            best_match_id=best.submission_id if best else None,
            best_similarity=best.similarity if best else 0.0,
            threshold=self.threshold,
            matches=matches,
            text=text,
        )

    def similarity(self, a: str, b: str) -> float:
        """Public helper: similarity between two raw strings."""
        ta, tb = _tokenize(a), _tokenize(b)
        ga, gb = _trigrams(a), _trigrams(b)
        tj = _jaccard(ta, tb)
        tg = _jaccard(ga, gb)
        return round(0.5 * tj + 0.5 * tg, 4)
