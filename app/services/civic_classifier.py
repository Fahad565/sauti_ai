"""Civic issue classifier for Sprint 6 Feature 6.1.

Classifies raw citizen submissions into one of nine high-level civic
categories using deterministic keyword/heuristic rules. Returns a
confidence score in ``[0.0, 1.0]``.

The categories are intentionally aligned to the FEATURES.md Sprint 6
deliverable:

    - Roads
    - Healthcare
    - Water
    - Education
    - Markets
    - Security
    - Environment
    - Housing
    - Sanitation
    - Transport

The classifier is pure-function — no LLM calls, no DB access — so it
is cheap to call from REST, webhook, or batch analytics paths.

Design reference: DECISION-0017.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional


# Canonical civic categories produced by this service.
CIVIC_CATEGORIES: List[str] = [
    "Roads",
    "Healthcare",
    "Water",
    "Education",
    "Markets",
    "Security",
    "Environment",
    "Housing",
    "Sanitation",
    "Transport",
]

# Per-trigger weight.  Multi-word phrases and domain-specific keywords
# count more than single-word overlaps.  This lets "school roof" beat
# out an incidental "leaking" match for the Water bucket.
CATEGORY_KEYWORDS: Dict[str, Dict[str, float]] = {
    "Roads": {
        "road": 1.0, "roads": 1.0, "pothole": 1.5, "potholes": 1.5,
        "street": 0.7, "highway": 1.0, "tarmac": 1.2, "asphalt": 1.2,
        "lane": 0.5, "carriageway": 1.0, "roundabout": 1.0,
        "sign": 0.4, "signal": 0.5, "speed bump": 1.5, "speedbumps": 1.5,
    },
    "Healthcare": {
        "hospital": 2.0, "clinic": 1.8, "dispensary": 1.8,
        "health centre": 1.5, "health centre": 1.5,
        "doctor": 1.5, "doctors": 1.5, "nurse": 1.5, "nurses": 1.5,
        "ambulance": 2.0, "medicine": 1.5, "drug": 1.0,
        "pharmacy": 1.5, "patient": 1.0, "maternity": 1.8,
        "vaccination": 1.5, "casualty": 1.8,
        "medical": 1.0, "health facility": 1.5, "healthcare": 1.5,
    },
    "Water": {
        "water": 0.6, "tap": 1.5, "pipes": 1.5, "pipe": 1.5,
        "leak": 1.4, "leaking": 1.4, "leakage": 1.4,
        "burst": 1.5, "no water": 2.5, "dry": 0.8,
        "desalination": 1.5, "kiosk": 1.0, "supply": 0.7,
        "aquifer": 1.5, "reservoir": 1.5, "drinking": 1.0,
        "potable": 1.2,
    },
    "Education": {
        "school": 1.6, "schools": 1.6, "primary": 1.0,
        "secondary": 1.0, "college": 1.5, "university": 1.5,
        "classroom": 2.0, "teacher": 1.5, "pupil": 1.5,
        "student": 1.0, "students": 1.0, "library": 1.5,
        "textbook": 1.5, "academy": 1.5, "kindergarten": 1.5,
        "vocational": 1.5, "exam": 0.8, "learning": 0.7,
        "tuition": 1.5, "schoolchildren": 2.0,
    },
    "Markets": {
        "market": 1.4, "markets": 1.4, "stall": 1.5,
        "stalls": 1.5, "vendor": 1.5, "vendors": 1.5,
        "trading": 0.7, "wholesale": 1.2, "retail": 0.8,
        "produce": 0.7, "goods": 0.5, "hawker": 1.5,
        "shopping": 0.6, "price": 0.4, "merchandise": 1.0,
    },
    "Security": {
        "police": 1.5, "security": 1.0, "crime": 1.4,
        "robbery": 2.0, "robbed": 2.0, "theft": 1.8,
        "stolen": 1.8, "attack": 1.8, "violence": 1.5,
        "unsafe": 1.0, "gang": 1.7, "gangster": 1.7,
        "patrol": 1.0, "robbers": 1.8, "murder": 2.0,
        "assault": 1.7, "burglary": 1.7,
    },
    "Environment": {
        "environment": 1.0, "tree": 0.7, "trees": 0.7,
        "forest": 1.2, "pollution": 1.5, "smoke": 1.0,
        "air quality": 1.8, "flood": 1.2, "flooding": 1.2,
        "erosion": 1.2, "climate": 1.0, "deforestation": 1.8,
        "wetland": 1.5, "mangrove": 1.5, "wildlife": 1.5,
        "carbon": 1.0,
    },
    "Housing": {
        "house": 0.7, "houses": 0.7, "housing": 1.2,
        "estate": 0.8, "home": 0.5, "homeless": 1.5,
        "shelter": 1.2, "rent": 1.5, "landlord": 1.5,
        "tenant": 1.5, "eviction": 1.8, "roof": 0.8,
        "apartment": 1.0, "flat": 0.7, "household": 0.7,
        "residential": 0.8,
    },
    "Sanitation": {
        "garbage": 2.0, "waste": 1.0, "sewer": 2.0,
        "sewage": 2.0, "drainage": 1.8, "drain": 1.5,
        "toilet": 1.8, "latrine": 1.5, "sanitation": 1.5,
        "refuse": 1.5, "dump": 1.5, "rubbish": 1.5,
        "trash": 1.2, "filthy": 1.2, "uncollected": 2.0,
    },
    "Transport": {
        "transport": 1.0, "matatu": 1.8, "bus": 1.0,
        "buses": 1.0, "taxi": 1.0, "tuktuk": 1.5,
        "ferry": 1.5, "train": 1.2, "sgr": 1.5,
        "airport": 1.2, "traffic": 1.5, "parking": 1.0,
        "route": 0.4, "commute": 0.8, "fare": 0.8,
    },
}


@dataclass
class CivicClassification:
    """Result of classifying a citizen submission."""

    category: str
    confidence: float
    matched_keywords: List[str] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _tokenize(text: str) -> List[str]:
    """Lower-case and split into word tokens, preserving only alpha-numeric."""
    if not text:
        return []
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return [t.strip() for t in cleaned.split() if t.strip()]


class CivicClassifier:
    """Rule-based citizen-issue classifier.

    Returns one of ``CIVIC_CATEGORIES`` for every non-empty submission.
    Empty / whitespace-only submissions yield ``Sanitation`` with
    confidence ``0.0`` as a safe default (matches the existing
    classifier behaviour from Sprint 5).
    """

    def __init__(self, categories: Optional[List[str]] = None) -> None:
        self.categories = categories or CIVIC_CATEGORIES
        self.keywords: Dict[str, Dict[str, float]] = {
            cat: CATEGORY_KEYWORDS.get(cat, {}) for cat in self.categories
        }

    def classify(self, text: str) -> CivicClassification:
        """Classify a free-text submission into a civic category."""
        if not text or not text.strip():
            return CivicClassification(
                category="Sanitation",
                confidence=0.0,
                matched_keywords=[],
                scores={cat: 0.0 for cat in self.categories},
            )

        normalized = text.lower()
        scores: Dict[str, float] = {cat: 0.0 for cat in self.categories}
        matches: Dict[str, List[str]] = {cat: [] for cat in self.categories}

        for category, triggers in self.keywords.items():
            for trigger, weight in triggers.items():
                if trigger in normalized:
                    scores[category] += float(weight)
                    matches[category].append(trigger)

        # Best by raw score; tie-breaker is the order of CIVIC_CATEGORIES
        # (which encodes our domain priority).
        best_category = self.categories[0]
        best_score = -1.0
        for cat in self.categories:
            if scores[cat] > best_score:
                best_score = scores[cat]
                best_category = cat

        # If nothing matched at all, return a low-confidence "Sanitation"
        # default so callers always get a category.
        if best_score <= 0.0:
            return CivicClassification(
                category="Sanitation",
                confidence=0.30,
                matched_keywords=[],
                scores=scores,
            )

        # Confidence model: cap at 0.95, grow with raw score.
        confidence = min(0.95, round(0.55 + (best_score * 0.15), 2))

        return CivicClassification(
            category=best_category,
            confidence=confidence,
            matched_keywords=sorted(set(matches[best_category])),
            scores=scores,
        )

    def classify_batch(self, texts: List[str]) -> List[CivicClassification]:
        """Convenience method: classify many texts in order."""
        return [self.classify(t) for t in texts]
