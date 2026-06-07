"""
routers/extractions.py
-----------------------
Save extraction results to DB and retrieve them.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.database import get_db
from db.models import User, Contract, Clause, ExtractionSummary
from db.schemas import SummaryResponse, ClauseResponse
from auth.dependencies import get_current_user

router = APIRouter(prefix="/extractions", tags=["extractions"])


def gen_id(): return str(uuid.uuid4())


async def save_extraction_to_db(db: AsyncSession, contract_id: str, pipeline_result: dict):
    """Persist pipeline output to clauses + extraction_summaries tables."""
    summary_data = pipeline_result["summary"]
    tp = summary_data.get("transaction_price", {})
    ct = summary_data.get("contract_term", {})
    rr = summary_data.get("revenue_recognition", {})

    # Save summary
    summary = ExtractionSummary(
        id=gen_id(),
        contract_id=contract_id,
        total_clauses=summary_data.get("total_clauses_extracted", 0),
        total_contract_value_usd=tp.get("total_contract_value_usd", 0.0),
        duration_months=ct.get("duration_months"),
        license_type=rr.get("license_type"),
        recognition_pattern=rr.get("recognition_pattern"),
        has_variable_consideration=tp.get("has_variable_consideration", False),
        has_refund_rights=summary_data.get("has_refund_rights", False),
        auto_renewal=ct.get("auto_renewal", False),
        average_confidence=summary_data.get("average_confidence", 0.0),
        clauses_by_type=summary_data.get("clauses_by_type", {}),
        risk_flags=summary_data.get("asc606_risk_flags", []),
        extractor_coverage=pipeline_result.get("extractor_coverage", {}),
    )
    db.add(summary)

    # Save individual clauses
    for clause_data in pipeline_result.get("clauses", []):
        clause = Clause(
            id=gen_id(),
            contract_id=contract_id,
            clause_type=clause_data.get("clause_type", ""),
            asc606_step=clause_data.get("asc606_step"),
            asc606_relevance=clause_data.get("asc606_relevance"),
            section=clause_data.get("section", ""),
            parent_article=clause_data.get("parent_article"),
            extracted_text=clause_data.get("extracted_text", ""),
            confidence=clause_data.get("confidence", 0.0),
            extracted_values=clause_data.get("extracted_values", {}),
            flags=clause_data.get("flags", []),
        )
        db.add(clause)

    await db.flush()


@router.get("/{contract_id}/summary", response_model=SummaryResponse)
async def get_summary(
    contract_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify ownership
    contract_res = await db.execute(
        select(Contract).where(Contract.id == contract_id, Contract.org_id == current_user.org_id)
    )
    if not contract_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    result = await db.execute(
        select(ExtractionSummary).where(ExtractionSummary.contract_id == contract_id)
    )
    summary = result.scalar_one_or_none()
    if not summary:
        raise HTTPException(status_code=404, detail="Extraction not complete yet")
    return SummaryResponse.model_validate(summary)


@router.get("/{contract_id}/clauses", response_model=list[ClauseResponse])
async def get_clauses(
    contract_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    clause_type: str = None,
):
    contract_res = await db.execute(
        select(Contract).where(Contract.id == contract_id, Contract.org_id == current_user.org_id)
    )
    if not contract_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contract not found")

    query = select(Clause).where(Clause.contract_id == contract_id)
    if clause_type:
        query = query.where(Clause.clause_type == clause_type.upper())

    result = await db.execute(query)
    return [ClauseResponse.model_validate(c) for c in result.scalars().all()]
