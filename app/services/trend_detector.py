"""Trend detection service for Sprint 6 Feature 6.6.

Aggregates submissions over a recent time window and surfaces four
"trend shape" signals:

1. Volume trend            — is the submission count increasing,
                              decreasing, or flat over the window?
2. Emerging hotspots       — which constituencies have moved up the
                              volume ranking when compared to the
                              prior window?
3. Recurring failures      — submissions that look like duplicates of
                              each other inside the window.
4. Seasonal pulse          — simple weekly bucket counts so a dashboard
                              can render a sparkline.

Inputs are pulled directly from the Submission repository — no LLM,
no external service.  Output is a structured dictionary suitable for
serialisation into a JSON dashboard response.

Design reference: DECISION-0022.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from collections import Counter, defaultdict

from sqlalchemy.orm import Session

from app.models.domain import Submission
from app.services.duplicate_detector import DuplicateDetector


DEFAULT_WINDOW_DAYS = 7
DEFAULT_COMPARE_WINDOW_DAYS = 7


@dataclass
class TrendVolume:
    """Per-day submission count series."""

    daily: Dict[str, int] = field(default_factory=dict)
    total: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Hotspot:
    """A constituency that moved up the volume ranking."""

    constituency: str
    current_volume: int
    previous_volume: int
    delta: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RecurringFailure:
    """A cluster of similar submissions inside the window."""

    canonical_text: str
    submission_ids: List[int]
    similarity: float
    count: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TrendReport:
    """Top-level aggregation returned by the trend detector."""

    window_start: str
    window_end: str
    previous_window_start: Optional[str]
    previous_window_end: Optional[str]
    total_volume: int
    previous_volume: int
    direction: str  # "rising" | "falling" | "flat"
    weekly_pulse: Dict[str, int]
    hotspots: List[Hotspot] = field(default_factory=list)
    recurring_failures: List[RecurringFailure] = field(default_factory=list)
    top_categories: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        out = asdict(self)
        out["hotspots"] = [h.to_dict() for h in self.hotspots]
        out["recurring_failures"] = [r.to_dict() for r in self.recurring_failures]
        return out


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


class TrendDetector:
    """Aggregate submissions into a structured trend report."""

    def __init__(
        self,
        db: Session,
        window_days: int = DEFAULT_WINDOW_DAYS,
        compare_window_days: int = DEFAULT_COMPARE_WINDOW_DAYS,
    ) -> None:
        self.db = db
        self.window_days = window_days
        self.compare_window_days = compare_window_days

    def _window(self) -> tuple[datetime, datetime, datetime, datetime]:
        now = datetime.now(timezone.utc)
        current_start = now - timedelta(days=self.window_days)
        previous_end = current_start
        previous_start = previous_end - timedelta(days=self.compare_window_days)
        return current_start, now, previous_start, previous_end

    def _normalize_dt(self, dt) -> datetime:
        """SQLite stores naive datetimes; coerce them to UTC-aware."""
        if dt is None:
            return datetime.now(timezone.utc)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def detect(self, *, top_n_categories: int = 5) -> TrendReport:
        current_start, current_end, previous_start, previous_end = self._window()

        current_submissions = (
            self.db.query(Submission)
            .filter(Submission.submitted_at != None)  # noqa: E711
            .filter(Submission.submitted_at <= current_end)
            .all()
        )
        # Filter to current window with normalised datetimes (SQLite stores naive).
        current_submissions = [
            s for s in current_submissions
            if self._normalize_dt(s.submitted_at) >= current_start
        ]

        previous_submissions = (
            self.db.query(Submission)
            .filter(Submission.submitted_at != None)  # noqa: E711
            .filter(Submission.submitted_at < previous_end)
            .all()
        )
        previous_submissions = [
            s for s in previous_submissions
            if self._normalize_dt(s.submitted_at) >= previous_start
        ]  

        # Volume + direction
        total_current = len(current_submissions)
        total_previous = len(previous_submissions)
        if total_previous == 0:
            direction = "rising" if total_current > 0 else "flat"
        else:
            ratio = total_current / total_previous
            if ratio >= 1.20:
                direction = "rising"
            elif ratio <= 0.80:
                direction = "falling"
            else:
                direction = "flat"

        # Weekly pulse: split the window into 7 day buckets (or
        # ``window_days`` of equal-sized buckets if window_days < 7).
        weekly_pulse: Dict[str, int] = defaultdict(int)
        bucket_size = max(1, self.window_days // 7 or 1)
        for s in current_submissions:
            if s.submitted_at is None:
                continue
            submitted = self._normalize_dt(s.submitted_at)
            elapsed = (current_end - submitted).days
            bucket_idx = max(0, elapsed // bucket_size)
            weekly_pulse[f"bucket_{bucket_idx}"] += 1
        # Sort the bucket keys numerically for deterministic output.
        weekly_pulse = {k: weekly_pulse[k] for k in sorted(weekly_pulse)}

        # Hotspots: compare constituency volume
        current_by_constituency = Counter(s.constituency for s in current_submissions if s.constituency)
        previous_by_constituency = Counter(s.constituency for s in previous_submissions if s.constituency)

        hotspots: List[Hotspot] = []
        all_constituencies = set(current_by_constituency) | set(previous_by_constituency)
        for c in sorted(all_constituencies):
            cur = current_by_constituency.get(c, 0)
            prev = previous_by_constituency.get(c, 0)
            delta = cur - prev
            if delta >= 2:  # threshold for "emerging"
                hotspots.append(
                    Hotspot(constituency=c, current_volume=cur, previous_volume=prev, delta=delta)
                )
        hotspots.sort(key=lambda h: h.delta, reverse=True)

        # Recurring failures: cluster high-similarity submissions.
        recurring: List[RecurringFailure] = []
        if current_submissions:
            det = DuplicateDetector(self.db, threshold=0.55, time_window_days=self.window_days)
            seed_indices: set[int] = set()
            for s in current_submissions:
                if s.id in seed_indices:
                    continue
                result = det.detect(s.raw_content, constituency=s.constituency, candidates=current_submissions)
                cluster_ids = [m.submission_id for m in result.matches]
                if len(cluster_ids) >= 2:
                    avg = sum(m.similarity for m in result.matches) / max(1, len(result.matches))
                    recurring.append(
                        RecurringFailure(
                            canonical_text=s.raw_content,
                            submission_ids=cluster_ids,
                            similarity=round(avg, 4),
                            count=len(cluster_ids),
                        )
                    )
                    seed_indices.update(cluster_ids)

        # Top categories: emit the most common substring token across
        # the submission set so the dashboard can display it without
        # depending on the (out-of-this-service) intent classifier.
        cat_counter: Counter[str] = Counter()
        for s in current_submissions:
            text = (s.raw_content or "").lower()
            for kw in ("road", "water", "hospital", "school", "garbage", "pothole", "flood"):
                if kw in text:
                    cat_counter[kw] += 1
        top_categories = [
            {"keyword": kw, "count": cnt}
            for kw, cnt in cat_counter.most_common(top_n_categories)
        ]

        return TrendReport(
            window_start=_iso(current_start),
            window_end=_iso(current_end),
            previous_window_start=_iso(previous_start),
            previous_window_end=_iso(previous_end),
            total_volume=total_current,
            previous_volume=total_previous,
            direction=direction,
            weekly_pulse=dict(weekly_pulse),
            hotspots=hotspots,
            recurring_failures=recurring,
            top_categories=top_categories,
        )
