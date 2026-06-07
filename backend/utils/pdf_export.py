from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet

def generate_contract_pdf(filepath, contract, summary, clauses):
    doc = SimpleDocTemplate(filepath)

    styles = getSampleStyleSheet()

    content = []

    content.append(
        Paragraph(
            "SmartClause Contract Analysis Report",
            styles["Title"]
        )
    )

    content.append(Spacer(1, 20))

    content.append(
        Paragraph(
            f"Filename: {contract.filename}",
            styles["BodyText"]
        )
    )

    content.append(
        Paragraph(
            f"Contract Value: ${summary.total_contract_value_usd:,.0f}",
            styles["BodyText"]
        )
    )

    content.append(
        Paragraph(
            f"Duration: {summary.duration_months} months",
            styles["BodyText"]
        )
    )

    content.append(Spacer(1, 15))

    content.append(
        Paragraph(
            "ASC 606 Risk Flags",
            styles["Heading2"]
        )
    )

    for flag in summary.risk_flags:
        content.append(
            Paragraph(
                f"• {flag}",
                styles["BodyText"]
            )
        )

    content.append(PageBreak())

    content.append(
        Paragraph(
            "Extracted Clauses",
            styles["Heading1"]
        )
    )

    for clause in clauses:

        content.append(
            Paragraph(
                clause.clause_type,
                styles["Heading3"]
            )
        )

        content.append(
            Paragraph(
                f"Confidence: {round(clause.confidence*100)}%",
                styles["BodyText"]
            )
        )

        content.append(
            Paragraph(
                clause.extracted_text,
                styles["BodyText"]
            )
        )

        content.append(Spacer(1, 10))

    doc.build(content)