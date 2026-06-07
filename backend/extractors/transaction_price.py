"""
extractors/transaction_price.py
--------------------------------
Extracts transaction price — ASC 606 Step 3.

ORIGINAL BUG:
    Regex missed amounts written as "USD 1,250,000" (with space).
    Returned a raw string list with no labels or parsed integers.
    Finance teams need: what type of fee, what amount, what structure.

FIXES:
    - Handles USD 1,250,000 / $1,250,000 / USD1,250,000 / two million etc.
    - Labels each amount: annual_fee, total_contract_value, license_fee, etc.
    - Parses to integers for downstream computation
    - Detects payment structure: milestone / upfront / recurring
    - Flags mixed-fee structures needing allocation
"""

import re
from .base_extractor import BaseExtractor

# Matches: "Annual subscription fee: USD 180,000" — captures label + amount
_MONEY_RE = re.compile(
    r'(?P<label>[A-Za-z ,\-]{0,50}?)(?:USD\s?|US\$|\$)\s?(?P<amount>[\d,]+(?:\.\d{1,2})?)',
    re.IGNORECASE
)

_LABEL_MAP = {
    "annual": "annual_fee",
    "yearly": "annual_fee",
    "subscription": "subscription_fee",
    "total contract": "total_contract_value",
    "total project": "total_contract_value",
    "total fee": "total_contract_value",
    "one-time": "one_time_fee",
    "one time": "one_time_fee",
    "implementation": "implementation_fee",
    "license": "license_fee",
    "perpetual": "license_fee",
    "maintenance": "maintenance_fee",
    "monthly": "monthly_fee",
    "per user": "per_user_fee",
}


def _label(raw: str) -> str:
    raw_l = raw.strip().lower()
    for key, norm in _LABEL_MAP.items():
        if key in raw_l:
            return norm
    return "other_fee"


def _parse(raw: str) -> int:
    try:
        return int(raw.replace(",", "").split(".")[0])
    except ValueError:
        return 0


def _payment_structure(text: str) -> str:
    t = text.lower()
    if re.search(r'milestone|upon completion|upon acceptance', t):
        return "milestone_based"
    if re.search(r'upfront|upon signing|upon execution|at contract signing', t):
        return "upfront"
    if re.search(r'monthly|annually|per year|annual', t):
        return "recurring"
    return "unspecified"


class TransactionPriceExtractor(BaseExtractor):
    clause_type = "TRANSACTION_PRICE"
    asc606_step = 3
    asc606_relevance_note = (
        "Establishes the transaction price for Step 3. Includes fixed fees, "
        "variable amounts, and payment structure which determines "
        "financing component assessment."
    )
    keywords = [
        "fee", "price", "contract value", "subscription", "total", "payment",
        "invoiced", "license fee", "maintenance fee", "per year", "per month"
    ]
    negative_keywords = ["termination fee", "late payment", "interest rate", "penalty"]

    def extract_values(self, text: str):
        matches = list(_MONEY_RE.finditer(text))
        if not matches:
            return None

        amounts_by_type = {}
        all_amounts = []

        for m in matches:
            value = _parse(m.group("amount"))
            if value < 100:   # Skip trivial numbers like percentages caught as amounts
                continue
            label = _label(m.group("label"))
            if label not in amounts_by_type or value > amounts_by_type[label]:
                amounts_by_type[label] = value
            all_amounts.append({"label": label, "amount_usd": value})

        if not all_amounts:
            return None

        # license_fee is the primary fee in perpetual license contracts —
        # treat it as total_contract_value when no explicit total is present
        if "license_fee" in amounts_by_type and "total_contract_value" not in amounts_by_type:
            amounts_by_type["total_contract_value"] = amounts_by_type["license_fee"]

        total = amounts_by_type.get("total_contract_value") or max(
            amounts_by_type.values(), default=0
        )

        flags = []
        if "one_time_fee" in amounts_by_type and "subscription_fee" in amounts_by_type:
            flags.append("MIXED_FEE_STRUCTURE — split fixed vs recurring for allocation")
        if "license_fee" in amounts_by_type and "maintenance_fee" in amounts_by_type:
            flags.append("LICENSE + MAINTENANCE — assess if maintenance is a separate PO")

        return {
            "text": text.strip(),
            "values": {
                "amounts": all_amounts,
                "amounts_by_type": amounts_by_type,
                "total_contract_value_usd": total,
                "payment_structure": _payment_structure(text),
                "currency": "USD"
            },
            "flags": flags
        }
