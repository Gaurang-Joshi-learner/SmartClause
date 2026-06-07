"""
extractors/licensing.py
------------------------
Extracts license terms — ASC 606 Step 5.

ORIGINAL BUG:
    Default classification was "right-to-access" when "right to use"
    wasn't literally present. This is backwards — most on-prem perpetual
    licenses are right-to-use (point-in-time recognition).

    OVERCOUNTING BUG: "license" appears in many unrelated sections
    (limitation of liability, confidentiality, IP indemnity). The extractor
    was firing on all of them — 18 hits on contract_003.

FIXES:
    - Correct ASC 606-10-55-58 classification logic
    - negative_keywords excludes non-licensing sections
    - Only extracts from sections actually granting license rights
    - Requires a license GRANT signal, not just the word "license"
"""

import re
from .base_extractor import BaseExtractor

_USER_RE   = re.compile(r'(?:up\s+to\s+|maximum\s+)?(\d+)\s*concurrent\s+users?', re.IGNORECASE)
_SCOPE_RE  = re.compile(r'non[-\s]exclusive|exclusive|non[-\s]transferable|perpetual', re.IGNORECASE)
_GRANT_RE  = re.compile(
    r'(?:grants?|grant(?:ing|ed)?)\s+(?:[\w,\-]+\s+){0,8}(?:licen[sc]e|right\s+to\s+(?:use|access|install))'
    r'|licen[sc]ee\s+(?:shall|may)\s+(?:use|install|access)'
    r'|right\s+to\s+(?:use|access|install)\s+the\s+(?:software|platform|service)',
    re.IGNORECASE
)

_ACCESS_SIGNALS = [
    "right to access", "access the", "hosted", "cloud", "saas",
    "software as a service", "subscription", "as it exists throughout",
    "during the term", "as updated", "as maintained"
]
_USE_SIGNALS = [
    "right to use", "install and use", "perpetual", "on-premises", "on-premise",
    "as it exists at the time of delivery", "perpetual license", "functional copy"
]


def _classify(text: str) -> dict:
    t = text.lower()
    access_hits = sum(1 for s in _ACCESS_SIGNALS if s in t)
    use_hits    = sum(1 for s in _USE_SIGNALS    if s in t)

    if access_hits > use_hits:
        return {"license_type": "RIGHT_TO_ACCESS", "recognition_pattern": "OVER_TIME",
                "explanation": "Customer accesses evolving IP (SaaS/hosted) → recognize ratably"}
    if use_hits > 0:
        return {"license_type": "RIGHT_TO_USE", "recognition_pattern": "POINT_IN_TIME",
                "explanation": "Customer receives static copy (on-prem/perpetual) → recognize at delivery"}
    return {"license_type": "UNCLEAR", "recognition_pattern": "REQUIRES_REVIEW",
            "explanation": "Cannot determine — manual review needed per ASC 606-10-55-54"}


class LicensingExtractor(BaseExtractor):
    clause_type = "LICENSING"
    asc606_step = 5
    asc606_relevance_note = (
        "License type determines WHEN revenue is recognized (ASC 606-10-55-54): "
        "'Right to use' (static IP) = point-in-time. "
        "'Right to access' (evolving IP, SaaS) = over-time (ratable)."
    )
    keywords = [
        "license grant", "grants a license", "right to use", "right to access",
        "non-exclusive", "perpetual license", "install and use", "concurrent users",
        "licensee shall", "licensee may use"
    ]
    # Exclude sections that mention "license" in non-grant contexts
    negative_keywords = [
        "limitation of liability", "confidentiality", "indemnif",
        "governing law", "general provisions", "audit rights",
        "license-related claims"
    ]

    def extract_values(self, text: str):
        # Must have an actual license grant, not just the word "license"
        if not _GRANT_RE.search(text):
            return None

        classification = _classify(text)
        users  = _USER_RE.findall(text)
        scopes = list(set(s.lower() for s in _SCOPE_RE.findall(text)))

        restrictions = []
        if re.search(r'sublicens', text, re.IGNORECASE):
            allowed = "permitted" in text.lower()
            restrictions.append("sublicensing: " + ("permitted" if allowed else "prohibited"))
        if re.search(r'reverse\s+engineer', text, re.IGNORECASE):
            restrictions.append("reverse engineering: prohibited")

        flags = [f"{classification['recognition_pattern']}: {classification['explanation']}"]
        if classification["license_type"] == "UNCLEAR":
            flags.append("MANUAL_REVIEW_REQUIRED — license type ambiguous")

        return {
            "text": text.strip(),
            "values": {
                **classification,
                "max_concurrent_users": int(users[0]) if users else None,
                "license_scope_terms":  scopes,
                "restrictions":         restrictions
            },
            "flags": flags
        }
