"""
extractors/milestones.py
-------------------------
Extracts milestone and acceptance criteria — ASC 606 Step 5.

ORIGINAL BUG:
    Returned raw section text only. Zero structured extraction.
    Milestones have rich data: name, deliverable, due date, payment %,
    acceptance window — all critical for revenue timing.

FIXES:
    - Parses individual milestone entries with name and payment trigger %
    - Extracts acceptance windows and deemed-acceptance language
    - Flags customer-controlled acceptance (delays revenue recognition)
    - Flags deemed-acceptance clauses (protects provider's revenue timing)
"""

import re
from .base_extractor import BaseExtractor

_MILESTONE_RE = re.compile(
    r'(?:Milestone\s+\d+|M\d+)[:\s]+([^\n]{5,80})',
    re.IGNORECASE
)
_PAYMENT_PCT_RE = re.compile(
    r'(\d+)\s*%\s*(?:of\s+(?:total\s+)?fees?|payment)',
    re.IGNORECASE
)
_ACCEPTANCE_WINDOW_RE = re.compile(
    r'(\d+)\s*(?:business\s+)?days?\s*(?:to\s+(?:review|accept|approve)|acceptance\s+period)',
    re.IGNORECASE
)
_DUE_RE = re.compile(r'(?:due\s+date|target\s+date|by)[:\s]+([^\n]{5,60})', re.IGNORECASE)


def _parse_milestones(text: str) -> list:
    names = _MILESTONE_RE.findall(text)
    pcts  = _PAYMENT_PCT_RE.findall(text)
    return [
        {"name": name.strip(), "payment_trigger_pct": int(pcts[i]) if i < len(pcts) else None}
        for i, name in enumerate(names)
    ]


class MilestonesExtractor(BaseExtractor):
    clause_type = "MILESTONES"
    asc606_step = 5
    asc606_relevance_note = (
        "Milestones define point-in-time recognition events. "
        "Acceptance criteria and deemed-acceptance clauses control "
        "when revenue can be recognized for each deliverable."
    )
    keywords = [
        "milestone", "acceptance", "deliverable", "sign-off", "go-live",
        "acceptance criteria", "kickoff", "phase", "deemed accepted"
    ]

    def extract_values(self, text: str):
        milestones   = _parse_milestones(text)
        due_dates    = [m.group(1).strip() for m in _DUE_RE.finditer(text)]
        acc_windows  = [int(m.group(1)) for m in _ACCEPTANCE_WINDOW_RE.finditer(text)]

        deemed_acceptance = bool(re.search(
            r'deemed\s+accept|shall\s+be\s+deemed|if\s+customer\s+does\s+not\s+(?:reject|provide)',
            text, re.IGNORECASE
        ))
        customer_signoff = bool(re.search(
            r'customer\s+(?:written\s+)?(?:sign[- ]off|acceptance|approval)',
            text, re.IGNORECASE
        ))

        if not milestones and not deemed_acceptance and not customer_signoff:
            return None

        pct_total = sum(m["payment_trigger_pct"] or 0 for m in milestones)

        flags = []
        if deemed_acceptance:
            flags.append("DEEMED_ACCEPTANCE — recognize revenue after silent review period")
        if customer_signoff and not deemed_acceptance:
            flags.append("CUSTOMER_SIGN-OFF_REQUIRED — revenue blocked until explicit acceptance")
        if pct_total > 0:
            flags.append(f"MILESTONE_PAYMENTS total {pct_total}% of contract value")

        return {
            "text": text.strip(),
            "values": {
                "milestones":                    milestones,
                "milestone_count":               len(milestones),
                "due_dates":                     due_dates,
                "acceptance_window_days":        max(acc_windows, default=None),
                "has_deemed_acceptance":         deemed_acceptance,
                "customer_sign_off_required":    customer_signoff
            },
            "flags": flags
        }
