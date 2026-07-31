"""Priority / Severity scoring service for Sprint 6 Feature 6.3.

Estimates the urgency of a citizen submission on the four-level scale
required by FEATURES.md::

    Critical
    High
    Medium
    Low

The scorer is intentionally heuristic — no LLM, no DB — so it is
cheap to run from every webhook. It blends five signals:

* urgency keyword density (life, leak, emergency, fire, ...)        +x
* complaint vocabulary density (broken, no water, damaged, ...)     +x
* category severity (Healthcare > Roads > Markets, ...)            +x
* duplicate score (multiple complaints about the same thing ->     +x
                   recurring problem is worse)
* length/emphasis signals (all caps, repetition)                   +x

Each signal contributes a bounded amount and the total is mapped
onto the four-level scale.

Design reference: DECISION-0019.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional


PRIORITY_LEVELS: List[str] = ["Critical", "High", "Medium", "Low"]


# Words / phrases that signal direct safety risk.
URGENCY_KEYWORDS: Dict[str, int] = {
    "fire": 6, "flood": 6, "flooding": 6, "emergency": 6,
    "life": 5, "death": 6, "dead": 5, "dying": 5, "injury": 5,
    "injured": 5, "accident": 5, "collapse": 6, "collapsed": 6,
    "electrocution": 8, "live wire": 8, "downed power line": 8,
    "sparking": 5, "explosion": 8, "gas leak": 8,
    "outbreak": 6, "epidemic": 7, "cholera": 8,
    "ambulance": 5, "pregnant": 4, "baby": 3, "child": 3,
    "children": 4, "schoolchildren": 4, "kid": 3, "kids": 3,
    "robbed": 5, "robbery": 6, "attack": 5, "gun": 6, "gunshot": 7,
    "no water": 3, "no electricity": 4, "no power": 4,
}


# Words / phrases that signal a complaint (negative state).
COMPLAINT_KEYWORDS: Dict[str, int] = {
    "broken": 2, "damaged": 2, "leak": 2, "leaking": 2,
    "overflowing": 3, "burst": 3, "blocked": 2,
    "pothole": 2, "potholes": 3, "garbage": 2, "waste": 1, "dump": 2,
    "uncollected": 2, "dry": 2, "dark": 2, "unsafe": 3,
    "stolen": 2, "theft": 3, "delay": 1, "delayed": 2,
    "poor": 2, "issue": 1, "problem": 1,
    "overflows": 3, "sewage": 3, "smell": 2, "stink": 2,
    "not working": 2, "doesn't work": 2, "hasn't worked": 2,
    "failing": 2, "failed": 2,
}


# Category-level severity floor.  Healthcare/Water/Security get higher
# base scores than Markets/Transport.
CATEGORY_SEVERITY: Dict[str, int] = {
    "Healthcare": 8,
    "Security": 8,
    "Water": 6,
    "Sanitation": 6,
    "Environment": 5,
    "Roads": 5,
    "Housing": 5,
    "Education": 4,
    "Markets": 3,
    "Transport": 3,
}


@dataclass
class PriorityScore:
    """Priority score returned by the scorer."""

    level: str
    score: float
    category: Optional[str] = None
    signals: Dict[str, float] = field(default_factory=dict)
    rationale: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _normalize(text: str) -> str:
    return (text or "").lower()


def _caps_intensity(text: str) -> float:
    """Return 0..1 indicating how much the message is in ALL CAPS."""
    if not text:
        return 0.0
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 4:
        return 0.0
    upper = sum(1 for c in letters if c.isupper())
    return round(upper / len(letters), 2)


def _repetition_intensity(text: str) -> float:
    """Return 0..1 for repeated emphasis (e.g. "very very very")."""
    if not text:
        return 0.0
    tokens = [t for t in re.findall(r"\w+", text.lower()) if len(t) > 1]
    if len(tokens) < 2:
        return 0.0
    counts: Dict[str, int] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1
    max_count = max(counts.values())
    if max_count < 2:
        return 0.0
    return round(min(1.0, (max_count - 1) / 4.0), 2)


class PriorityScorer:
    """Score a citizen submission on a 4-level urgency scale."""

    def __init__(self, thresholds: Optional[Dict[str, float]] = None) -> None:
        self.thresholds = thresholds or {
            "Critical": 12.0,
            "High": 7.0,
            "Medium": 5.0,
            "Low": 0.0,
        }

    def _signals(
        self,
        text: str,
        category: Optional[str],
        duplicate_count: int,
    ) -> Dict[str, float]:
        norm = _normalize(text)

        urgency = 0
        for kw, weight in URGENCY_KEYWORDS.items():
            if kw in norm:
                urgency += weight

        complaint = 0
        for kw, weight in COMPLAINT_KEYWORDS.items():
            if kw in norm:
                complaint += weight

        category_score = CATEGORY_SEVERITY.get(category or "", 0)
        dup_score = min(8.0, duplicate_count * 2.0)  # each duplicate -> +2, capped +8
        emphasis = (_caps_intensity(text) + _repetition_intensity(text)) * 1.5

        return {
            "urgency": float(urgency),
            "complaint": float(complaint),
            "category_floor": float(category_score),
            "duplicate_pressure": float(dup_score),
            "emphasis": round(emphasis, 2),
        }

    def _level(self, total: float) -> str:
        if total >= self.thresholds["Critical"]:
            return "Critical"
        if total >= self.thresholds["High"]:
            return "High"
        if total >= self.thresholds["Medium"]:
            return "Medium"
        return "Low"

    def _rationale(self, signals: Dict[str, float], category: Optional[str]) -> List[str]:
        notes: List[str] = []
        if category:
            notes.append(f"Category '{category}' adds {signals['category_floor']:.1f} base severity.")
        if signals["urgency"] > 0:
            notes.append(f"Urgency keyword matches contributed {signals['urgency']:.1f}.")
        if signals["complaint"] > 0:
            notes.append(f"Complaint vocabulary contributed {signals['complaint']:.1f}.")
        if signals["duplicate_pressure"] > 0:
            notes.append(f"Duplicate pressure contributed {signals['duplicate_pressure']:.1f}.")
        if signals["emphasis"] >= 0.6:
            notes.append(f"High emphasis (CAPS/repetition) contributed {signals['emphasis']:.1f}.")
        if not notes:
            notes.append("No significant priority signals; defaulting to Low.")
        return notes

    def score(
        self,
        text: str,
        category: Optional[str] = None,
        duplicate_count: int = 0,
    ) -> PriorityScore:
        """Score the text. ``duplicate_count`` should be >= 0."""
        sigs = self._signals(text or "", category, duplicate_count)
        total = (
            sigs["urgency"]
            + sigs["complaint"]
            + sigs["category_floor"]
            + sigs["duplicate_pressure"]
            + sigs["emphasis"]
        )
        total = round(total, 2)
        level = self._level(total)
        return PriorityScore(
            level=level,
            score=total,
            category=category,
            signals=sigs,
            rationale=self._rationale(sigs, category),
        )
