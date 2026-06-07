"""
extractors/base_extractor.py
-----------------------------
Base class for all ASC 606 clause extractors.

IMPROVEMENTS OVER ORIGINAL:
  - Keyword matching checks BOTH section title AND content.
    Original only checked content — missing title-level signals
    like a "TERMINATION" section header.
  - negative_keywords: lets subclasses exclude false-positive sections.
  - Confidence is computed from keyword density, not hardcoded per-extractor.
  - Output includes parent_article, asc606_relevance note, and flags list.
"""


class BaseExtractor:
    clause_type: str = ""
    asc606_step = None
    asc606_relevance_note: str = ""
    keywords: list = []
    negative_keywords: list = []

    # ------------------------------------------------------------------ #
    #  Matching                                                            #
    # ------------------------------------------------------------------ #

    def match(self, section: dict) -> bool:
        """Check title AND content for keywords."""
        combined = (
            section.get("section_title", "") + " " + section.get("content", "")
        ).lower()

        if not any(kw.lower() in combined for kw in self.keywords):
            return False

        if self.negative_keywords:
            if any(nk.lower() in combined for nk in self.negative_keywords):
                return False

        return True

    def _base_confidence(self, text: str) -> float:
        """Confidence based on keyword density, capped at 0.97."""
        text_lower = text.lower()
        hits = sum(1 for kw in self.keywords if kw.lower() in text_lower)
        base = 0.60 + (hits / max(len(self.keywords), 1)) * 0.35
        return round(min(base, 0.97), 2)

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def extract(self, section: dict):
        if not self.match(section):
            return None

        extracted = self.extract_values(section["content"])
        if not extracted:
            return None

        return {
            "clause_type": self.clause_type,
            "asc606_step": self.asc606_step,
            "asc606_relevance": self.asc606_relevance_note,
            "section": section["section_title"],
            "parent_article": section.get("parent_article", ""),
            "extracted_text": extracted["text"],
            "confidence": extracted.get(
                "confidence", self._base_confidence(section["content"])
            ),
            "extracted_values": extracted.get("values") or {},
            "flags": extracted.get("flags") or []
        }

    def extract_values(self, text: str):
        raise NotImplementedError
