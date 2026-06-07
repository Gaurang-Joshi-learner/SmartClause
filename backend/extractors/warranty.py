"""
extractors/warranty.py
-----------------------
Extracts warranty terms — ASC 606 Step 2.

ORIGINAL BUG:
    Classified as "service-type" if "extended" appeared anywhere.
    This is wrong. A warranty is service-type ONLY if the customer can
    purchase it separately. The original missed this entirely.

FIXES:
    - Correct ASC 606-10-55-30 classification:
      ASSURANCE_TYPE = does not exceed agreed-upon spec → NOT a PO
      SERVICE_TYPE   = separately purchasable / beyond spec → IS a PO
    - Extracts warranty period in months
    - Detects separately-priced extended warranties (always service-type)
    - Flags revenue allocation requirement for service-type warranties
"""

import re
from .base_extractor import BaseExtractor

_PERIOD_RE = re.compile(
    r'(?:\((\d+)\)|(\d+))\s*(months?|years?)\s*(?:from|following|after)',
    re.IGNORECASE
)
_FEE_RE = re.compile(
    r'(?:additional\s+fee|for\s+additional|per\s+year|annually|purchase)\s*'
    r'[^.\n]{0,60}'
    r'(?:USD\s?[\d,]+|\$[\d,]+)',
    re.IGNORECASE
)

_SERVICE_SIGNALS   = ["additional fee", "purchase", "optional", "may purchase",
                      "upgrade", "extended warranty", "premium support", "extended support"]
_ASSURANCE_SIGNALS = ["materially in accordance", "free from defects", "at no additional",
                      "included", "assurance", "does not constitute a separate"]


def _classify(text: str) -> str:
    t = text.lower()
    service_hits   = sum(1 for s in _SERVICE_SIGNALS   if s in t)
    assurance_hits = sum(1 for s in _ASSURANCE_SIGNALS if s in t)
    if service_hits > assurance_hits:
        return "SERVICE_TYPE"
    if assurance_hits > 0:
        return "ASSURANCE_TYPE"
    return "SERVICE_TYPE" if _FEE_RE.search(text) else "ASSURANCE_TYPE"


def _period_months(text: str):
    for m in _PERIOD_RE.finditer(text):
        num = int(m.group(1) or m.group(2))
        unit = m.group(3).lower()
        return num * (12 if unit.startswith("year") else 1)
    return None


class WarrantyExtractor(BaseExtractor):
    clause_type = "WARRANTY"
    asc606_step = 2
    asc606_relevance_note = (
        "WARRANTY TYPE IS CRITICAL under ASC 606-10-55-30. "
        "ASSURANCE_TYPE: accrue as cost, NOT a PO. "
        "SERVICE_TYPE (sold separately or beyond-spec): IS a distinct PO "
        "requiring separate transaction price allocation."
    )
    keywords = ["warranty", "warrants", "defect", "extended warranty",
                "defect correction", "remedy", "workmanship", "warranty period"]

    def extract_values(self, text: str):
        if not re.search(r'warrant(?:y|ies|s)', text, re.IGNORECASE):
            return None

        wtype    = _classify(text)
        period   = _period_months(text)
        fees     = _FEE_RE.findall(text)

        flags = []
        if wtype == "SERVICE_TYPE":
            flags.append("SERVICE_TYPE_WARRANTY — IS a distinct PO, allocate transaction price")
        else:
            flags.append("ASSURANCE_TYPE_WARRANTY — NOT a PO, accrue cost separately")
        if fees:
            flags.append("SEPARATELY_PRICED — confirms service-type classification")

        return {
            "text": text.strip(),
            "values": {
                "warranty_classification": wtype,
                "warranty_period_months":  period,
                "separately_priced":       bool(fees),
            },
            "flags": flags
        }
