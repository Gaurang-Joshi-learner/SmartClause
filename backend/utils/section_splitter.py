"""
utils/section_splitter.py
--------------------------
Splits a contract into labelled sections by detecting headers.

ORIGINAL BUG (critical):
    re.split() with multiple capture groups produces None placeholders
    for non-matching groups. The original code did parts[i+1] assuming
    content was always the next element — it wasn't.
    Result: EVERY section had empty content. Zero extraction possible.

FIX:
    Use re.finditer() to locate header positions, then slice the raw text
    between consecutive header positions. Content is never lost.
"""

import re

_HEADER_PATTERN = re.compile(
    r'^('
    r'(?:ARTICLE|SECTION)\s+\d+[\w\s:,\-]*'    # ARTICLE 1: DEFINITIONS
    r'|\d+\.\d+(?:\.\d+)?\s+[A-Z][^\n]{2,}'    # 2.1 Software Platform Access
    r'|\d+\.\s+[A-Z][^\n]{2,}'                  # 1. SERVICES AND DELIVERABLES
    r')',
    re.MULTILINE
)


def _clean_title(title: str) -> str:
    """Remove trailing numbering artefacts left after slicing."""
    title = re.sub(r'\n+\d*$', '', title)
    return title.strip()


def split_into_sections(text: str) -> list:
    """
    Returns list of dicts:
        {
            "section_title": str,       # cleaned header text
            "parent_article": str,      # nearest ARTICLE/SECTION ancestor
            "content": str,             # text between this and next header
            "char_start": int           # offset in original text
        }
    """
    matches = list(_HEADER_PATTERN.finditer(text))

    if not matches:
        return [{
            "section_title": "FULL_DOCUMENT",
            "parent_article": "",
            "content": text.strip(),
            "char_start": 0
        }]

    sections = []
    current_article = ""

    for i, match in enumerate(matches):
        title = _clean_title(match.group())
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()

        if re.match(r'^(ARTICLE|SECTION)\s+\d+', title, re.IGNORECASE):
            current_article = title

        if not content:
            continue

        sections.append({
            "section_title": title,
            "parent_article": current_article,
            "content": content,
            "char_start": match.start()
        })

    return sections
