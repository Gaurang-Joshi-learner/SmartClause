"""
extractors/refund_rights.py
----------------------------
Extracts refund and return rights — ASC 606 Step 3.

ORIGINAL BUG:
    Returned raw text only — zero extraction. Refund rights create
    variable consideration that directly reduces the transaction price.
    The constraint test and refund liability recording depend on this data.

FIXES:
    - Classifies refund type: full / pro-rata / satisfaction guarantee
    - Extracts time windows and triggering conditions
    - Flags refund liability recording requirement
    - Flags constraint assessment per ASC 606-10-32-11
"""

import re
from .base_extractor import BaseExtractor

_WINDOW_RE    = re.compile(r'within\s+(?:\((\d+)\)|(\d+))\s*days?', re.IGNORECASE)
_CONDITION_RE = re.compile(
    r'(?:if|provided|in the event|due to|caused by)\s+([^.]{10,120})',
    re.IGNORECASE
)

_REFUND_TYPES = {
    "FULL_REFUND":            ["full refund", "all fees paid", "all amounts paid"],
    "PRO_RATA_REFUND":        ["pro-rata", "pro rata", "proportional", "unused portion", "prepaid"],
    "SATISFACTION_GUARANTEE": ["satisfaction guarantee", "money back", "not satisfied"],
    "PARTIAL_REFUND":         ["partial refund", "portion of fees"],
}


def _classify(text: str) -> list:
    t = text.lower()
    return [rt for rt, sigs in _REFUND_TYPES.items() if any(s in t for s in sigs)] or ["UNSPECIFIED_REFUND"]


def _get_window(text: str):
    for m in _WINDOW_RE.finditer(text):
        val = m.group(1) or m.group(2)
        if val:
            return int(val)
    return None


class RefundRightsExtractor(BaseExtractor):
    clause_type = "REFUND_RIGHTS"
    asc606_step = 3
    asc606_relevance_note = (
        "Refund rights create variable consideration that must be constrained "
        "under ASC 606-10-32-11. A refund liability must be recorded equal to "
        "the probability-weighted expected refund amount. Revenue cannot be "
        "recognized for amounts likely to be refunded."
    )
    keywords = [
        "refund", "money back", "pro-rata", "pro rata",
        "satisfaction guarantee", "prepaid fees", "unused portion"
    ]

    def extract_values(self, text: str):
        if not re.search(r'refund|money\s+back', text, re.IGNORECASE):
            return None

        refund_types = _classify(text)
        window       = _get_window(text)
        conditions   = [m.group(1).strip() for m in _CONDITION_RE.finditer(text)][:3]

        is_guarantee = "SATISFACTION_GUARANTEE" in refund_types
        is_pro_rata  = "PRO_RATA_REFUND" in refund_types

        flags = []
        if is_guarantee:
            flags.append("SATISFACTION_GUARANTEE — defer revenue until refund window closes")
        if is_pro_rata:
            flags.append("PRO_RATA_REFUND — record refund liability for at-risk prepaid amounts")
        if window:
            flags.append(f"REFUND_WINDOW: {window} days — monitor claims in this period")
        flags.append("RECORD_REFUND_LIABILITY = probability-weighted expected refund")

        return {
            "text": text.strip(),
            "values": {
                "refund_types":              refund_types,
                "refund_window_days":        window,
                "triggering_conditions":     conditions,
                "is_satisfaction_guarantee": is_guarantee,
                "is_pro_rata":               is_pro_rata,
            },
            "flags": flags
        }
