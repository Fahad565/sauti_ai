"""Intent Classifier service for Sauti AI.

Classifies incoming citizen messages into intent categories with confidence scoring.
"""

from __future__ import annotations

import re
from typing import Dict, Any


class IntentClassifier:
    """Rule-based and heuristic intent classifier for civic inquiries."""

    INFRASTRUCTURE_KEYWORDS = {
        "hospital", "clinic", "dispensary", "school", "academy", "road", "bridge",
        "market", "water", "borehole", "pipe", "well", "drainage", "sewer", "light",
        "street light", "facility", "building", "hall", "stadium"
    }

    PROJECT_KEYWORDS = {
        "project", "construction", "tarmac", "upgrading", "renovation",
        "cdf", "budget", "completion", "ongoing", "planned", "development project"
    }

    COMPLAINT_KEYWORDS = {
        "broken", "damaged", "leak", "leaking", "overflowing", "garbage", "waste", "pothole",
        "uncollected", "dry", "no water", "dark", "unsafe", "stolen", "corrupt", "delay", "poor", "issue", "problem"
    }

    STATUS_KEYWORDS = {
        "status", "progress", "when", "when will", "finish", "update", "is it finished", "completion date",
        "stage", "how far", "timeline"
    }

    def classify(self, text: str) -> Dict[str, Any]:
        """Classify inbound message text into standard intent category."""
        if not text or not text.strip():
            return {
                "intent": "general_question",
                "confidence": 0.5,
                "keywords_matched": [],
            }

        cleaned = text.lower().strip()

        scores: Dict[str, float] = {
            "infrastructure_lookup": 0.0,
            "project_lookup": 0.0,
            "complaint": 0.0,
            "status_update": 0.0,
            "general_question": 0.1,  # Baseline score
        }

        matched_kw = []

        for kw in self.INFRASTRUCTURE_KEYWORDS:
            if kw in cleaned:
                scores["infrastructure_lookup"] += 1.5
                matched_kw.append(kw)

        for kw in self.PROJECT_KEYWORDS:
            if kw in cleaned:
                scores["project_lookup"] += 1.5
                matched_kw.append(kw)

        for kw in self.COMPLAINT_KEYWORDS:
            if kw in cleaned:
                scores["complaint"] += 2.0
                matched_kw.append(kw)

        for kw in self.STATUS_KEYWORDS:
            if kw in cleaned:
                scores["status_update"] += 1.5
                matched_kw.append(kw)

        # Disambiguation heuristics
        if any(w in cleaned for w in self.COMPLAINT_KEYWORDS):
            scores["complaint"] += 2.0

        if "when" in cleaned or "status" in cleaned or "progress" in cleaned or "finish" in cleaned:
            scores["status_update"] += 1.0

        if "project" in cleaned and not ("when" in cleaned or "finish" in cleaned):
            scores["project_lookup"] += 1.5

        top_intent = max(scores, key=lambda k: scores[k])
        max_score = scores[top_intent]

        # Calculate confidence
        if max_score <= 0.1:
            intent = "general_question"
            confidence = 0.6
        else:
            intent = top_intent
            confidence = min(0.95, round(0.5 + (max_score * 0.15), 2))

        return {
            "intent": intent,
            "confidence": confidence,
            "scores": scores,
            "keywords_matched": list(set(matched_kw)),
        }
