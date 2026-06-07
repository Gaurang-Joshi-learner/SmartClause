"""
utils/pdf_reader.py
--------------------
Converts PDF bytes to plain text using pdfplumber.
"""

import pdfplumber
import io


def read_pdf(file_bytes: bytes) -> str:
    text = ""
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"PDF parsing error: {e}")
        return ""
    return text