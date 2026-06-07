"""
extractors/contract_duration.py
--------------------------------
Extracts contract term and renewal — ASC 606 Step 5.

ORIGINAL BUG:
    Pattern r'(\d+\s?(months|years))' missed "Eight (8) months" and
    "thirty-six (36) months" — the parenthetical form used in contracts.
    Also, picking the largest number returned 60 (from "60 days notice")
    instead of 36 (the actual term), because "days" wasn't excluded.

FIXES:
    - Handles parenthetical form: "Eight (8) months" → 8
    - Handles plain form: "36 months" → 36
    - Excludes day-only references from duration calculation
    - Correctly identifies renewal term separately from initial term
    - Detects "Eight months" (written-out) via word-to-number map
"""

import re
from .base_extractor import BaseExtractor

_WORD_NUMS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "eighteen": 18, "twenty-four": 24,
    "thirty": 30, "thirty-six": 36, "forty-eight": 48, "sixty": 60
}

# "thirty-six (36) months" or "(36) months" or "36 months"
_PAREN_MONTHS_RE = re.compile(r'\((\d+)\)\s*months?', re.IGNORECASE)
_PAREN_YEARS_RE  = re.compile(r'\((\d+)\)\s*years?',  re.IGNORECASE)
_PLAIN_MONTHS_RE = re.compile(r'(?<!\()\b(\d+)\s*[-–]?\s*months?(?!\s*\))', re.IGNORECASE)
_PLAIN_YEARS_RE  = re.compile(r'(?<!\()\b(\d+)\s*[-–]?\s*years?(?!\s*\))',  re.IGNORECASE)

_DATE_RE = re.compile(
    r'(?:effective\s+date|commencement)[^\n]{0,30}?'
    r'(\b(?:January|February|March|April|May|June|July|'
    r'August|September|October|November|December)'
    r'\s+\d{1,2},?\s+\d{4})',
    re.IGNORECASE
)
_RENEWAL_NOTICE_RE = re.compile(r'\((\d+)\)\s*days?\s*(?:prior|before|written)', re.IGNORECASE)
_AUTO_RENEWAL_RE   = re.compile(r'auto(?:matically)?\s+renew|successive\s+\w+\s+term', re.IGNORECASE)


def _extract_months(text: str) -> list:
    """Return all month-durations found, parenthetical form takes priority."""
    results = []
    # Parenthetical (most reliable — "thirty-six (36) months")
    results += [int(x) * 1   for x in _PAREN_MONTHS_RE.findall(text)]
    results += [int(x) * 12  for x in _PAREN_YEARS_RE.findall(text)]
    # Plain digit form only if no parenthetical found for this unit
    if not _PAREN_MONTHS_RE.search(text):
        results += [int(x) for x in _PLAIN_MONTHS_RE.findall(text) if int(x) <= 120]
    if not _PAREN_YEARS_RE.search(text):
        results += [int(x) * 12 for x in _PLAIN_YEARS_RE.findall(text) if int(x) <= 10]
    # Written-out numbers ("Eight months")
    for word, num in _WORD_NUMS.items():
        if re.search(rf'\b{word}\b\s*\(?\d*\)?\s*months?', text, re.IGNORECASE):
            results.append(num)
    return results


class ContractDurationExtractor(BaseExtractor):
    clause_type = "CONTRACT_DURATION"
    asc606_step = 5
    asc606_relevance_note = (
        "Contract term defines the revenue recognition period. Auto-renewals may "
        "constitute contract modifications under ASC 606-10-25-12, requiring "
        "reassessment of performance obligations and transaction price."
    )
    keywords = [
        "initial term", "term", "months", "years", "renewal", "effective date",
        "commencement", "subscription term", "license term", "expiration", "duration"
    ]
    negative_keywords = ["warranty period", "support term only"]

    def extract_values(self, text: str):
        durations = _extract_months(text)
        if not durations:
            return None

        # Initial term = largest duration found; renewal = second largest if distinct
        durations_sorted = sorted(set(durations), reverse=True)
        initial_term = durations_sorted[0]
        renewal_term = durations_sorted[1] if len(durations_sorted) > 1 else None

        dates = [m.group(1) for m in _DATE_RE.finditer(text)]
        auto_renew = bool(_AUTO_RENEWAL_RE.search(text))
        notice_days_list = [int(m.group(1)) for m in _RENEWAL_NOTICE_RE.finditer(text)]
        notice_days = max(notice_days_list, default=None)
        is_perpetual = bool(re.search(r'perpetual|no\s+expir|indefinite', text, re.IGNORECASE))

        flags = []
        if auto_renew:
            flags.append("AUTO_RENEWAL — assess if renewal is modification or continuation")
        if is_perpetual:
            flags.append("PERPETUAL/EVERGREEN — no fixed end date, recognize over service period")
        if initial_term > 24:
            flags.append(f"LONG-TERM CONTRACT ({initial_term}mo) — monitor for modifications")

        return {
            "text": text.strip(),
            "values": {
                "initial_term_months": initial_term,
                "renewal_term_months": renewal_term,
                "auto_renewal": auto_renew,
                "renewal_notice_days": notice_days,
                "effective_dates": dates,
                "is_perpetual": is_perpetual
            },
            "flags": flags
        }
