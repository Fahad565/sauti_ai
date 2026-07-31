"""Topic tagging service for Sprint 6 Feature 6.5.

Assigns multiple topic tags to a citizen submission, with a score for
each tag.  Tags are useful both for human dashboards (e.g. filtering
issues for an MP's weekly brief) and for aggregation across similar
threads (Feature 6.6 — Trend Detection).

A tag is included if it scores above ``MIN_TAG_SCORE`` (0.15).  The
results are returned sorted by score descending and capped at
``MAX_TAGS`` so a single noisy submission cannot flood the dashboard
with every tag.

Design reference: DECISION-0021.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional


# Each tag has a list of lexical triggers and a per-match weight.
# Multi-word phrases count for more (and have explicit weights).
TOPIC_TRIGGERS: Dict[str, Dict[str, float]] = {
    "Roads": {
        "road": 1.0, "roads": 1.0, "pothole": 1.5, "potholes": 1.5,
        "street": 1.0, "tarmac": 1.0, "lane": 0.5, "highway": 0.7,
    },
    "Flooding": {
        "flood": 2.0, "flooding": 2.0, "floods": 2.0,
        "water logged": 1.5, "waterlogged": 1.5, "deluge": 2.0,
        "overflows": 1.0, "overflow": 1.0,
    },
    "Bridges": {
        "bridge": 1.5, "bridges": 1.5, "footbridge": 1.7,
        "overpass": 1.0, "flyover": 1.0,
    },
    "Water Supply": {
        "water": 1.0, "tap": 1.2, "kiosk": 1.0, "pipe": 1.2,
        "leak": 1.0, "leaking": 1.0, "no water": 2.0,
        "low pressure": 1.5, "desalination": 1.0,
    },
    "Sanitation": {
        "garbage": 1.5, "waste": 1.2, "sewer": 1.7,
        "sewage": 1.7, "drain": 1.5, "drainage": 1.5,
        "toilet": 1.5, "latrine": 1.0, "refuse": 1.0,
        "rubbish": 1.0, "filthy": 1.2,
    },
    "Safety": {
        "accident": 1.5, "dangerous": 1.5, "unsafe": 1.5,
        "fire": 2.0, "collapse": 1.5, "collapse risk": 2.0,
        "live wire": 2.0, "sparking": 1.5,
    },
    "Children": {
        "child": 1.0, "children": 1.2, "kid": 0.8,
        "kids": 0.8, "schoolchildren": 1.5, "pupil": 0.8,
        "baby": 1.0, "toddler": 1.0,
    },
    "Schools": {
        "school": 1.0, "schools": 1.0, "primary": 0.8,
        "secondary": 0.8, "college": 1.0, "university": 1.0,
        "classroom": 1.0, "teacher": 0.8, "library": 0.7,
        "vocational": 1.0,
    },
    "Hospitals": {
        "hospital": 1.5, "clinic": 1.2, "dispensary": 1.2,
        "doctors": 1.0, "nurse": 1.0, "ambulance": 1.5,
        "medicine": 1.0, "patient": 0.8, "maternity": 1.5,
        "casualty": 1.5, "pharmacy": 1.0,
    },
    "Security": {
        "police": 1.0, "security": 1.0, "crime": 1.0, "robbery": 1.5,
        "robbed": 1.5, "theft": 1.5, "stolen": 1.5, "attack": 1.5,
        "violence": 1.5, "gang": 1.5, "patrol": 0.8, "unsafe": 0.5,
    },
    "Markets": {
        "market": 1.0, "stall": 1.2, "vendor": 1.2,
        "wholesale": 1.0, "retail": 0.7, "goods": 0.7,
        "hawker": 1.2,
    },
    "Environment": {
        "environment": 1.0, "tree": 0.7, "trees": 0.7,
        "forest": 1.0, "pollution": 1.5, "smoke": 1.0,
        "air quality": 1.5, "erosion": 1.0,
        "deforestation": 1.5, "wetland": 1.0, "mangrove": 1.0,
        "climate": 1.0,
    },
    "Housing": {
        "house": 0.8, "houses": 0.8, "housing": 1.0, "estate": 0.8,
        "shelter": 1.0, "rent": 1.0, "landlord": 1.0,
        "tenant": 1.0, "eviction": 1.5, "apartment": 0.8,
        "household": 0.7,
    },
    "Transport": {
        "transport": 1.0, "matatu": 1.5, "bus": 0.8,
        "buses": 0.8, "taxi": 0.8, "tuktuk": 1.0,
        "ferry": 1.2, "train": 1.0, "sgr": 1.2,
        "traffic": 1.5, "parking": 0.8, "route": 0.5,
        "fare": 0.8,
    },
}


MIN_TAG_SCORE = 0.15
MAX_TAGS = 8


@dataclass
class TopicTag:
    """A topic tag with its score."""

    tag: str
    score: float
    matched_triggers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TopicTaggingResult:
    """Aggregate result of running topic tagging on a text."""

    tags: List[TopicTag] = field(default_factory=list)
    text: str = ""

    @property
    def top_tag(self) -> Optional[str]:
        return self.tags[0].tag if self.tags else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "tags": [t.to_dict() for t in self.tags],
            "top_tag": self.top_tag,
        }


class TopicTagger:
    """Multi-label tagger for civic submissions."""

    def __init__(
        self,
        triggers: Optional[Dict[str, Dict[str, float]]] = None,
        min_score: float = MIN_TAG_SCORE,
        max_tags: int = MAX_TAGS,
    ) -> None:
        self.triggers = triggers or TOPIC_TRIGGERS
        self.min_score = min_score
        self.max_tags = max_tags

    def tag(self, text: str) -> TopicTaggingResult:
        if not text or not text.strip():
            return TopicTaggingResult(tags=[], text=text or "")

        norm = text.lower()

        tags: List[TopicTag] = []
        for tag, triggers in self.triggers.items():
            matched: List[str] = []
            score = 0.0
            # Sort triggers longest-first so multi-word phrases win over
            # their substrings.
            for trigger, weight in sorted(triggers.items(), key=lambda kv: len(kv[0]), reverse=True):
                if trigger in norm:
                    score += weight
                    matched.append(trigger)
            if score > 0:
                tags.append(TopicTag(tag=tag, score=round(score, 2), matched_triggers=matched))

        tags.sort(key=lambda t: t.score, reverse=True)

        # Apply thresholds + cap.
        filtered = [t for t in tags if t.score >= self.min_score][: self.max_tags]

        return TopicTaggingResult(tags=filtered, text=text)
