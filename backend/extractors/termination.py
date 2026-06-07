"""
extractors/termination.py
--------------------------
Extracts termination clauses.

ORIGINAL BUG:
    extract_values() had NO guard — it returned text for ANY section
    that mentioned "terminate" anywhere, even in passing.
    Produced false positives across almost every section.

FIXES:
    - Requires actual termination clause language (for cause / for convenience)
    - Distinguishes termination types: cause vs convenience
    - Extracts notice period and cure period separately
    - Detects termination fees (variable consideration link)
    - Flags contract existence risk for ASC 606 Step 1
"""

import re
from .base_extractor import BaseExtractor

_NOTICE_RE = re.compile(r'\((\d+)\)\s*days?\s*(?:written\s+)?notice', re.IGNORECASE)
_CURE_RE    = re.compile(r'(?:cure|remedy)\s+within\s+(?:\((\d+)\)|(\d+))\s*days?', re.IGNORECASE)
_TERM_FEE_RE = re.compile(
    r'(?:termination\s+fee|early\s+termination|cancellation\s+fee)'
    r'[^.\n]{0,100}'
    r'(?:USD\s?[\d,]+|\$[\d,]+|\d+\s*%)',
    re.IGNORECASE
)


class TerminationExtractor(BaseExtractor):
    clause_type = "TERMINATION"
    asc606_step = None
    asc606_relevance_note = (
        "Termination clauses affect contract existence (ASC 606 Step 1). "
        "Termination for convenience with fees may indicate the customer's "
        "substantive obligation to pay — affecting the contract term for recognition."
    )
    keywords = [
        "termination for convenience", "termination for cause",
        "termination for breach", "right to terminate",
        "may terminate", "terminate this agreement",
        "notice of termination", "early exit", "effect of termination"
    ]
    negative_keywords = ["data export upon termination", "intellectual property"]

    def extract_values(self, text: str):
        if not re.search(r'terminat(?:e|ion)\s+for\s+(?:cause|convenience|breach)', text, re.IGNORECASE):
            if not re.search(r'right\s+to\s+terminat|may\s+terminat', text, re.IGNORECASE):
                return None

        for_cause       = bool(re.search(r'for\s+cause|material\s+breach|insolvency|bankruptcy', text, re.IGNORECASE))
        for_convenience = bool(re.search(r'for\s+convenience|without\s+cause|for\s+any\s+reason', text, re.IGNORECASE))

        notice_list  = [int(m.group(1)) for m in _NOTICE_RE.finditer(text)]
        cure_matches = _CURE_RE.findall(text)
        cure_list    = [int(a or b) for a, b in cure_matches if a or b]
        term_fees    = _TERM_FEE_RE.findall(text)

        flags = []
        if term_fees:
            flags.append("TERMINATION_FEE — include in variable consideration assessment")
        if for_cause:
            flags.append("FOR_CAUSE — material breach criteria define contract enforceability (Step 1)")
        if for_convenience and not term_fees:
            flags.append("FOR_CONVENIENCE (no fee) — customer can exit freely; affects contract term")

        return {
            "text": text.strip(),
            "values": {
                "termination_for_cause":       for_cause,
                "termination_for_convenience": for_convenience,
                "notice_period_days":          max(notice_list, default=None),
                "cure_period_days":            max(cure_list, default=None),
                "termination_fees_found":      term_fees
            },
            "flags": flags
        }
