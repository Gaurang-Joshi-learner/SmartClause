"""
extractors/payment_terms.py
----------------------------
Extracts payment terms — ASC 606 Step 3.

ORIGINAL BUG:
    Pattern r'(\d+\s?days)' missed "thirty (30) days" — contracts write
    day counts as "word (number)" format. Zero hits on contract_001.

FIXES:
    - Handles both "30 days" and "thirty (30) days" via parenthetical pattern
    - Detects Net X terms, milestone triggers, advance payment
    - Flags financing component risk per ASC 606-10-32-15
    - Extracts late payment interest rates
"""

import re
from .base_extractor import BaseExtractor

# Matches "thirty (30) days" and "30 days"
_PAREN_DAYS_RE = re.compile(r'\((\d+)\)\s*days?', re.IGNORECASE)
_DIGIT_DAYS_RE = re.compile(r'(?:net\s*|within\s*|due\s+(?:within\s*)?)(\d+)\s*days?', re.IGNORECASE)
_INTEREST_RE = re.compile(
    r'(\d+(?:\.\d+)?)\s*%\s*(?:per\s+month|per\s+annum|p\.?a\.?|monthly|annually)',
    re.IGNORECASE
)
_UPON_RE = re.compile(
    r'(?:payable|due|invoiced?)\s+(?:upon|on|at)\s+([^.]{5,80})',
    re.IGNORECASE
)
_ADVANCE_RE = re.compile(
    r'in\s+advance|upfront|upon\s+signing|upon\s+execution|at\s+contract\s+signing',
    re.IGNORECASE
)


def _get_day_terms(text: str) -> list:
    """Collect all payment day durations from both parenthetical and plain forms."""
    paren = [int(x) for x in _PAREN_DAYS_RE.findall(text)]
    plain = [int(x) for x in _DIGIT_DAYS_RE.findall(text)]
    # Deduplicate: paren numbers are authoritative
    combined = list(set(paren + plain))
    # Filter: exclude tiny numbers (likely not payment terms) and milestone day counts
    return [d for d in combined if 5 <= d <= 180]


class PaymentTermsExtractor(BaseExtractor):
    clause_type = "PAYMENT_TERMS"
    asc606_step = 3
    asc606_relevance_note = (
        "Payment timing affects financing component assessment under ASC 606-10-32-15. "
        "If >12 months separate payment from service delivery, a significant financing "
        "component must be assessed and interest imputed."
    )
    keywords = [
        "net 30", "net 45", "net 60", "due within", "payable", "invoice",
        "payment terms", "billing", "in advance", "upon signing", "upon execution",
        "interest", "late payment", "days of invoice"
    ]
    negative_keywords = ["early termination", "termination fee", "notice period"]

    def extract_values(self, text: str):
        day_terms = _get_day_terms(text)
        interest = [m.group(0).strip() for m in _INTEREST_RE.finditer(text)]
        triggers = [m.group(1).strip() for m in _UPON_RE.finditer(text)]
        is_advance = bool(_ADVANCE_RE.search(text))

        if not day_terms and not triggers and not is_advance:
            return None

        financing_risk = is_advance and bool(
            re.search(r'annual|year|12\s*month', text, re.IGNORECASE)
        )

        flags = []
        if financing_risk:
            flags.append("FINANCING_COMPONENT_RISK — advance payment may require interest imputation")
        if interest:
            flags.append(f"LATE_PAYMENT_INTEREST: {', '.join(interest)}")
        if day_terms and max(day_terms) > 45:
            flags.append(f"EXTENDED_TERMS ({max(day_terms)} days) — assess financing component")

        return {
            "text": text.strip(),
            "values": {
                "payment_due_days": day_terms,
                "payment_triggers": triggers,
                "is_advance_payment": is_advance,
                "late_payment_interest": interest,
                "financing_component_risk": financing_risk
            },
            "flags": flags
        }
