"""Geographic extraction service for Sprint 6 Feature 6.4.

Extracts structured geographic information from a citizen submission:

* County           (e.g. "Mombasa")
* Constituency     (one of the 6 known constituencies)
* Ward             (e.g. "Kongowea", "Old Town")
* Landmark         (e.g. "Likoni Ferry", "Nyali Bridge")
* Road reference   (e.g. "Moi Avenue", "Nyali Road")
* Facility mention (e.g. "Coast General Hospital")

The extraction is deterministic — substring / token matching over a
seeded gazetteer that mirrors the seeded infrastructure data plus the
civic geography of Mombasa County.  The service can fall back on
``User.constituency`` (i.e. the citizen's registered constituency
from their WhatsApp profile) when no name is found in the message.

Design reference: DECISION-0020.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Set


COUNTIES: List[str] = ["Mombasa"]

CONSTITUENCIES: List[str] = [
    "Likoni",
    "Mvita",
    "Nyali",
    "Kisauni",
    "Changamwe",
    "Jomvu",
]

# Wards that show up in the seed data and frequently in citizen reports.
WARDS: List[str] = [
    "Mtongwe",
    "Bofu",
    "Likoni Town",
    "Shelly Beach",
    "Tudor",
    "Old Town",
    "Majengo",
    "Frere Town",
    "Kongowea",
    "Maweni",
    "Cadiz",
    "Bamburi",
    "Magogoni",
    "Mjambere",
    "Kiembeni",
    "Utange",
    "Airport",
    "Chaani",
    "Kipevu",
    "Port Reitz",
    "Magongo",
    "Miritini",
    "Mikindani",
    "Jomvu Kuu",
    "Owino Uhuru",
]

# High-profile landmarks observed in seed data and frequently cited
# in citizen feedback.
LANDMARKS: List[str] = [
    "Likoni Ferry",
    "Likoni Floating Footbridge",
    "Nyali Bridge",
    "Nyali New Creek Bridge",
    "Bamburi Footbridge",
    "Mvita Mackinnon Market",
    "Mvita Coast General Hospital",
    "Mvita Digo Road",
    "Kongowea Market",
    "Nyali Beach",
    "Jomvu-Miritini Interchange",
    "SGR Terminal",
    "Magongo Junction",
    "Mombasa Port",
    "Old Town",
    "Tudor Creek",
    "Mtongwe",
    "Bamburi Cement",
]

# Major roads commonly referenced. These overlap with seeded
# infrastructure but are kept distinct so a road can be detected even
# when its parent infrastructure row is not yet in the DB.
ROADS: List[str] = [
    "Moi Avenue",
    "Digo Road",
    "Nyali Road",
    "Bamburi Road",
    "Jomo Kenyatta Avenue",
    "Haile Selassie Road",
    "Mbaraki Road",
    "Nkrumah Road",
    "Tom Mboya Street",
    "Mwinyi Haji Road",
    "Links Road",
    "Beach Road",
    "Likoni Road",
    "Mombasa Road",
    "Kilindini Road",
    "Miritini Road",
    "Magongo Road",
]

# Public facilities frequently cited.
FACILITIES: List[str] = [
    "Coast General Hospital",
    "Likoni Sub-County Hospital",
    "Nyali Health Centre",
    "Mvita Coast General Hospital Annex",
    "Kisauni Dispensary",
    "Jomvu Model Health Centre",
    "Likoni Primary School",
    "Mvita Secondary School",
    "Nyali Girls High School",
    "Kisauni Technical Institute",
    "Changamwe Secondary School",
    "Jomvu Primary School",
    "Likoni Municipal Market",
    "Mvita Mackinnon Market",
    "Nyali Kongowea Market",
    "Kisauni Bamburi Market",
    "Changamwe West Market",
    "Jomvu Owino Uhuru Market",
]


@dataclass
class GeographicExtraction:
    """Result of running geo extraction on a text."""

    county: Optional[str] = None
    constituency: Optional[str] = None
    ward: Optional[str] = None
    landmarks: List[str] = field(default_factory=list)
    roads: List[str] = field(default_factory=list)
    facilities: List[str] = field(default_factory=list)
    fallback_used: bool = False
    confidence: float = 0.0
    matched_terms: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _contains_any(text: str, candidates: List[str]) -> List[str]:
    """Return candidates that appear as substrings of ``text``."""
    norm = text.lower() if text else ""
    found: List[str] = []
    for cand in candidates:
        if cand.lower() in norm:
            found.append(cand)
    return found


class GeographicExtractor:
    """Resolve the geographic references inside a citizen submission."""

    def __init__(
        self,
        counties: Optional[List[str]] = None,
        constituencies: Optional[List[str]] = None,
        wards: Optional[List[str]] = None,
        landmarks: Optional[List[str]] = None,
        roads: Optional[List[str]] = None,
        facilities: Optional[List[str]] = None,
    ) -> None:
        self.counties = counties or COUNTIES
        self.constituencies = constituencies or CONSTITUENCIES
        self.wards = wards or WARDS
        self.landmarks = landmarks or LANDMARKS
        self.roads = roads or ROADS
        self.facilities = facilities or FACILITIES

    def extract(
        self,
        text: str,
        fallback_constituency: Optional[str] = None,
    ) -> GeographicExtraction:
        """Extract geographic references from ``text``.

        ``fallback_constituency`` (typically ``User.constituency``) is
        used only when no constituency is found in the message itself.
        """
        matches: List[str] = []
        landmarks: List[str] = []
        roads: List[str] = []
        facilities: List[str] = []

        wards = _contains_any(text or "", self.wards)
        matches.extend(wards)

        counties = _contains_any(text or "", self.counties)
        matches.extend(counties)

        # Constituencies: prefer exact case-preserved match (Likoni / Nyali)
        constituency: Optional[str] = None
        norm_tokens = set(re.findall(r"\w+", (text or "").lower()))
        for name in self.constituencies:
            if name.lower() in norm_tokens or name.lower() in (text or "").lower():
                constituency = name
                matches.append(name)
                break

        landmarks = _contains_any(text or "", self.landmarks)
        for lm in landmarks:
            matches.append(lm)

        # Roads and facilities — sort by length desc so multi-word matches
        # are detected before single-word substrings inside them.
        for source, bucket in (
            (sorted(self.roads, key=len, reverse=True), roads),
            (sorted(self.facilities, key=len, reverse=True), facilities),
        ):
            seen: Set[str] = set()
            for cand in source:
                if cand.lower() in (text or "").lower():
                    if cand not in seen:
                        bucket.append(cand)
                        matches.append(cand)
                        seen.add(cand)

        fallback_used = False
        if not constituency and fallback_constituency:
            # Use the caller-supplied constituency silently (e.g. from
            # the user's profile) and mark the result as such.
            for known in self.constituencies:
                if fallback_constituency.strip().lower() == known.lower():
                    constituency = known
                    fallback_used = True
                    break

        # Confidence — weighting by how many fields were filled.
        filled = sum(
            1
            for v in (constituency, wards[0] if wards else None, landmarks[0] if landmarks else None)
            if v
        )
        if constituency and (landmarks or facilities or roads):
            confidence = 0.9
        elif constituency and wards:
            confidence = 0.75
        elif constituency:
            confidence = 0.6
        elif filled >= 2:
            confidence = 0.5
        elif filled == 1:
            confidence = 0.3
        else:
            confidence = 0.0

        # The gazetteer is Mombasa-only, so the default county is always
        # Mombasa unless the caller has supplied a different one.
        county = (
            counties[0]
            if counties
            else (self.counties[0] if self.counties else None)
        )

        return GeographicExtraction(
            county=county,
            constituency=constituency,
            ward=wards[0] if wards else None,
            landmarks=sorted(set(landmarks)),
            roads=sorted(set(roads), key=len, reverse=True),
            facilities=sorted(set(facilities), key=len, reverse=True),
            fallback_used=fallback_used,
            confidence=confidence,
            matched_terms=sorted(set(matches)),
        )
