"""
main_pipeline.py
-----------------
Orchestrates ASC 606 clause extraction.

KEY FIXES OVER ORIGINAL:
  1. Two-pass extraction: section-level first, then full-document fallback
     for any extractor that got zero hits. Catches cross-section clauses.
  2. Deduplication by (clause_type, section) — keeps highest-confidence hit.
  3. Output sorted by ASC 606 step order (useful to finance teams).
  4. Rich summary: total value, duration, license type, recognition pattern,
     all risk flags consolidated at the top level.
  5. extractor_coverage map shows which extractors fired and how many times
     (useful for debugging and QA).
"""

from datetime import datetime
from utils.section_splitter import split_into_sections

from extractors.perf_obligations      import PerformanceObligationsExtractor
from extractors.transaction_price     import TransactionPriceExtractor
from extractors.variable_consideration import VariableConsiderationExtractor
from extractors.payment_terms         import PaymentTermsExtractor
from extractors.contract_duration     import ContractDurationExtractor
from extractors.termination           import TerminationExtractor
from extractors.warranty              import WarrantyExtractor
from extractors.licensing             import LicensingExtractor
from extractors.milestones            import MilestonesExtractor
from extractors.refund_rights         import RefundRightsExtractor

EXTRACTORS = [
    PerformanceObligationsExtractor(),
    TransactionPriceExtractor(),
    VariableConsiderationExtractor(),
    PaymentTermsExtractor(),
    ContractDurationExtractor(),
    TerminationExtractor(),
    WarrantyExtractor(),
    LicensingExtractor(),
    MilestonesExtractor(),
    RefundRightsExtractor(),
]


# ------------------------------------------------------------------ #
#  Post-processing helpers                                            #
# ------------------------------------------------------------------ #

def _deduplicate(clauses: list) -> list:
    """Keep highest-confidence clause per (clause_type, section) pair."""
    seen = {}
    for c in clauses:
        key = (c["clause_type"], c["section"])
        if key not in seen or c["confidence"] > seen[key]["confidence"]:
            seen[key] = c
    return list(seen.values())


def _sort_by_step(clauses: list) -> list:
    """Sort by ASC 606 step, then descending confidence within each step."""
    return sorted(clauses, key=lambda c: (c.get("asc606_step") or 99, -c.get("confidence", 0)))


def _build_summary(clauses: list) -> dict:
    def get(ctype):
        return [c for c in clauses if c["clause_type"] == ctype]

    # Transaction price — pick the clause with the highest total value
    tp_clauses = get("TRANSACTION_PRICE")
    total_value = max(
        (c["extracted_values"].get("total_contract_value_usd", 0) for c in tp_clauses),
        default=0
    )

    # Contract duration
    dur = get("CONTRACT_DURATION")
    duration_months = dur[0]["extracted_values"].get("initial_term_months") if dur else None
    auto_renewal    = dur[0]["extracted_values"].get("auto_renewal", False) if dur else False

    # License
    lic = get("LICENSING")
    license_type        = lic[0]["extracted_values"].get("license_type")         if lic else None
    recognition_pattern = lic[0]["extracted_values"].get("recognition_pattern")  if lic else None

    # Warranty
    war = get("WARRANTY")
    has_service_warranty = any(
        c["extracted_values"].get("warranty_classification") == "SERVICE_TYPE" for c in war
    )

    # Variable consideration
    vc = get("VARIABLE_CONSIDERATION")
    vc_types = list(set(
        t for c in vc for t in c["extracted_values"].get("variable_consideration_types", [])
    ))

    # Milestones
    ms = get("MILESTONES")
    milestone_count = sum(c["extracted_values"].get("milestone_count", 0) for c in ms)

    # All flags
    all_flags = [
        f"[{c['clause_type']}] {flag}"
        for c in clauses for flag in c.get("flags", [])
    ]

    return {
        "total_clauses_extracted": len(clauses),
        "clauses_by_type": {
            ct: len(get(ct)) for ct in [
                "PERFORMANCE_OBLIGATION", "TRANSACTION_PRICE", "VARIABLE_CONSIDERATION",
                "PAYMENT_TERMS", "CONTRACT_DURATION", "TERMINATION",
                "WARRANTY", "LICENSING", "MILESTONES", "REFUND_RIGHTS"
            ]
        },
        "transaction_price": {
            "total_contract_value_usd":    total_value,
            "has_variable_consideration":  len(vc) > 0,
            "variable_consideration_types": vc_types,
        },
        "contract_term": {
            "duration_months": duration_months,
            "auto_renewal":    auto_renewal,
        },
        "performance_obligations": {
            "count":                       len(get("PERFORMANCE_OBLIGATION")),
            "has_service_type_warranty":   has_service_warranty,
            "milestone_count":             milestone_count,
        },
        "revenue_recognition": {
            "license_type":        license_type,
            "recognition_pattern": recognition_pattern,
        },
        "has_refund_rights":   len(get("REFUND_RIGHTS")) > 0,
        "average_confidence":  round(
            sum(c.get("confidence", 0) for c in clauses) / max(len(clauses), 1), 3
        ),
        "asc606_risk_flags":   all_flags,
    }


# ------------------------------------------------------------------ #
#  Main entry point                                                    #
# ------------------------------------------------------------------ #

def run_pipeline_from_text(text: str, filename: str = "uploaded_contract") -> dict:
    """
    Two-pass extraction:
      Pass 1 — all extractors on each section (section-specific clauses)
      Pass 2 — zero-hit extractors on full document (cross-section clauses)
    """
    sections = split_into_sections(text)
    clauses = []
    hits = {type(e).__name__: 0 for e in EXTRACTORS}

    # Pass 1: section-level
    for section in sections:
        for extractor in EXTRACTORS:
            result = extractor.extract(section)
            if result:
                clauses.append(result)
                hits[type(extractor).__name__] += 1

    # Pass 2: full-document fallback for zero-hit extractors
    full_doc = {
        "section_title": "FULL_DOCUMENT_SCAN",
        "parent_article": "",
        "content": text,
        "char_start": 0
    }
    for extractor in EXTRACTORS:
        name = type(extractor).__name__
        if hits[name] == 0:
            result = extractor.extract(full_doc)
            if result:
                result["section"] = "(full-document scan — no dedicated section found)"
                clauses.append(result)

    clauses = _deduplicate(clauses)
    clauses = _sort_by_step(clauses)
    summary = _build_summary(clauses)

    return {
        "contract_file":      filename,
        "extraction_timestamp": datetime.now().isoformat(),
        "extractor_coverage": hits,
        "summary":            summary,
        "clauses":            clauses,
    }
