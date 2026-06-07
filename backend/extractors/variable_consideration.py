"""
extractors/variable_consideration.py
--------------------------------------
Extracts variable consideration — ASC 606 Step 3.

ORIGINAL BUG:
    Pattern r'(\d+%)' returned only percentages, missing:
    - Dollar-denominated bonuses ("USD 25,000 bonus")
    - SLA credits (most common variable consideration in SaaS contracts)
    - No classification of type: discount / bonus / penalty / credit

FIXES:
    - Classifies into: DISCOUNT, INCENTIVE_BONUS, PENALTY, SERVICE_CREDIT
    - Extracts both percentage and dollar forms
    - Captures triggering conditions ("if uptime < 99.5%")
    - Flags whether constraint estimation is needed per ASC 606-10-32-11
"""

import re
from .base_extractor import BaseExtractor

_PERCENT_RE = re.compile(r'(\d+(?:\.\d+)?)\s*%')
_MONEY_RE = re.compile(r'(?:USD\s?|US\$|\$)\s?([\d,]+)', re.IGNORECASE)
_CONDITION_RE = re.compile(
    r'(?:if|when|provided|subject to|in the event|upon|exceeds?|falls?\s+below)'
    r'[^.]{5,120}',
    re.IGNORECASE
)

_VC_TYPES = {
    "DISCOUNT":          ["discount", "reduction", "reduced rate", "early payment"],
    "INCENTIVE_BONUS":   ["bonus", "incentive", "award", "performance bonus", "early completion"],
    "PENALTY":           ["penalty", "delay fee", "liquidated damages", "deduction"],
    "SERVICE_CREDIT":    ["credit", "service credit", "sla credit", "uptime credit"],
    "REFUND_ADJUSTMENT": ["refund", "rebate", "clawback"],
}


def _classify(text: str) -> list:
    t = text.lower()
    return [vt for vt, signals in _VC_TYPES.items() if any(s in t for s in signals)] or ["UNCLASSIFIED"]


def _needs_constraint(text: str) -> bool:
    signals = ["if", "provided that", "subject to", "contingent", "discretion",
               "customer approval", "satisfaction", "nps", "adoption rate"]
    return sum(1 for s in signals if s in text.lower()) >= 2


class VariableConsiderationExtractor(BaseExtractor):
    clause_type = "VARIABLE_CONSIDERATION"
    asc606_step = 3
    asc606_relevance_note = (
        "Variable consideration must be estimated and included in transaction price "
        "only to the extent it is probable of not reversing (constraint test, "
        "ASC 606-10-32-11). Each type needs separate estimation."
    )
    keywords = [
        "discount", "bonus", "credit", "penalty", "incentive", "service level",
        "sla", "uptime", "performance bonus", "early payment", "volume discount",
        "delay", "liquidated"
    ]

    def extract_values(self, text: str):
        percentages = _PERCENT_RE.findall(text)
        dollars = _MONEY_RE.findall(text)
        conditions = [c.strip() for c in _CONDITION_RE.findall(text)]

        if not percentages and not dollars:
            return None

        vc_types = _classify(text)
        constraint_needed = _needs_constraint(text)

        flags = []
        if constraint_needed:
            flags.append("CONSTRAINT_REQUIRED — apply ASC 606-10-32-11 before including in TP")
        if "PENALTY" in vc_types:
            flags.append("PENALTY — reduce transaction price when outcome is probable")
        if "SERVICE_CREDIT" in vc_types:
            flags.append("SLA_CREDIT — treat as variable price reduction, not separate obligation")
        if "INCENTIVE_BONUS" in vc_types:
            flags.append("PERFORMANCE_BONUS — include only when highly probable of achievement")

        return {
            "text": text.strip(),
            "values": {
                "variable_consideration_types": vc_types,
                "percentages": [f"{p}%" for p in percentages],
                "dollar_amounts": [f"USD {a}" for a in dollars],
                "triggering_conditions": conditions[:5],
                "constraint_assessment_required": constraint_needed,
            },
            "flags": flags
        }
