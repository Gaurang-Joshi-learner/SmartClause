"""
extractors/perf_obligations.py
-------------------------------
Extracts performance obligations — ASC 606 Step 2.

ORIGINAL BUG:
    extract_values() returned None unless "deliver" was in text.
    Missed: training, support, implementation, all described with
    "shall provide" instead of "shall deliver".

FIXES:
    - Multiple trigger verbs: deliver, provide, grant, perform, implement, train
    - Extracts individual obligation bullet points as a list
    - Detects DISTINCT obligations (separate PO → separate revenue allocation)
    - Flags over-time vs point-in-time recognition signals
"""

import re
from .base_extractor import BaseExtractor

_OBLIGATION_TRIGGERS = re.compile(
    r'shall\s+(?:deliver|provide|grant|perform|develop|implement|train|configure|migrate)'
    r'|(?:will|agrees\s+to)\s+(?:deliver|provide|grant|perform)'
    r'|(?:delivery|provision)\s+of'
    r'|(?:scope\s+of\s+(?:services|work)|deliverables?)',
    re.IGNORECASE
)

_BULLET_RE = re.compile(
    r'(?:^|\n)\s*(?:\([a-zA-Z]\)|\d+\.)\s*(.{10,120})',
    re.MULTILINE
)


def _extract_obligations(text: str) -> list:
    return [h.strip() for h in _BULLET_RE.findall(text) if h.strip()]


def _is_distinct(text: str) -> bool:
    signals = ["additional fee", "optional", "standalone", "separately", "purchase"]
    return any(s in text.lower() for s in signals)


class PerformanceObligationsExtractor(BaseExtractor):
    clause_type = "PERFORMANCE_OBLIGATION"
    asc606_step = 2
    asc606_relevance_note = (
        "Identifies distinct performance obligations. Each distinct PO requires "
        "separate revenue allocation and recognition timing under ASC 606 Step 2."
    )
    keywords = [
        "shall deliver", "shall provide", "scope of services", "deliverable",
        "implementation", "training", "support services", "license grant",
        "performance obligation", "scope of work", "services include"
    ]
    negative_keywords = ["termination", "governing law", "confidentiality"]

    def extract_values(self, text: str):
        has_trigger = bool(_OBLIGATION_TRIGGERS.search(text))
        has_scope = any(kw in text.lower() for kw in ["scope", "deliverable", "phase"])

        if not has_trigger and not has_scope:
            return None

        obligations = _extract_obligations(text)
        distinct = _is_distinct(text)

        flags = []
        if distinct:
            flags.append("DISTINCT_PO — allocate transaction price separately")
        if re.search(r'over\s+time|throughout|ratably|subscription', text, re.IGNORECASE):
            flags.append("RECOGNIZED_OVER_TIME — revenue spread across period")
        if re.search(r'upon\s+(?:delivery|acceptance|go-live|completion)', text, re.IGNORECASE):
            flags.append("POINT_IN_TIME_RECOGNITION")

        return {
            "text": text.strip(),
            "values": {
                "obligations_found": obligations if obligations else ["(see extracted text)"],
                "obligation_count": len(obligations) if obligations else 1,
                "is_distinct_obligation": distinct,
            },
            "flags": flags
        }
