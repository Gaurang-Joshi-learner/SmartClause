"""
routers/contracts.py
--------------------
Contract upload, listing, deletion, and status endpoints.
"""
import os
import aiofiles
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import selectinload
from fastapi.responses import FileResponse
from utils.pdf_export import generate_contract_pdf
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from db.database import get_db, settings
from db.models import User, Contract, ContractStatus
from db.schemas import ContractResponse, ContractDetailResponse
from auth.dependencies import get_current_user
from utils.pdf_reader import read_pdf
from main_pipeline import run_pipeline_from_text
from routers.extractions import save_extraction_to_db

router = APIRouter(prefix="/contracts", tags=["contracts"])


def gen_id(): return str(uuid.uuid4())


async def process_contract(contract_id: str, file_path: str, filename: str):
    """Background task: run extraction pipeline and save results."""
    from db.database import AsyncSessionLocal
    from db.models import Clause, ExtractionSummary

    async with AsyncSessionLocal() as db:
        try:
            # Read file
            if filename.lower().endswith(".pdf"):
                with open(file_path, "rb") as f:
                    text = read_pdf(f.read())
            else:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()

            if not text.strip():
                raise ValueError("Could not extract text from file")

            # Run pipeline
            result = run_pipeline_from_text(text, filename)

            # Save to DB
            await save_extraction_to_db(db, contract_id, result)

            # Update contract status
            res = await db.execute(select(Contract).where(Contract.id == contract_id))
            contract = res.scalar_one()
            contract.status = ContractStatus.DONE
            from datetime import datetime

            contract.processed_at = datetime.now()
            await db.commit()

        except Exception as e:
            res = await db.execute(select(Contract).where(Contract.id == contract_id))
            contract = res.scalar_one_or_none()
            if contract:
                contract.status = ContractStatus.FAILED
                contract.error_message = str(e)
                await db.commit()


@router.post("/upload", response_model=ContractResponse, status_code=201)
async def upload_contract(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validate file type
    if not file.filename.lower().endswith((".txt", ".pdf")):
        raise HTTPException(status_code=400, detail="Only .txt and .pdf files supported")

    # Read and validate size
    content = await file.read()
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_FILE_SIZE_MB}MB limit")

    # Save file to disk
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_id = gen_id()
    ext = os.path.splitext(file.filename)[1]
    file_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}{ext}")

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # Create contract record
    contract = Contract(
        id=file_id,
        org_id=current_user.org_id,
        user_id=current_user.id,
        filename=file.filename,
        file_path=file_path,
        file_size_bytes=len(content),
        status=ContractStatus.PROCESSING,
    )
    db.add(contract)
    await db.flush()

    # Queue background extraction
    background_tasks.add_task(process_contract, contract.id, file_path, file.filename)

    return ContractResponse.model_validate(contract)


@router.get("/", response_model=list[ContractResponse])
async def list_contracts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
):
    result = await db.execute(
        select(Contract)
        .where(Contract.org_id == current_user.org_id)
        .order_by(desc(Contract.created_at))
        .offset(skip).limit(limit)
    )
    return [ContractResponse.model_validate(c) for c in result.scalars().all()]


@router.get("/{contract_id}", response_model=ContractDetailResponse)
async def get_contract(
    contract_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Contract)
        .options(
            selectinload(Contract.summary),
            selectinload(Contract.clauses)
        )
        .where(
            Contract.id == contract_id,
            Contract.org_id == current_user.org_id
        )
    )

    contract = result.scalar_one_or_none()

    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    return ContractDetailResponse.model_validate(contract)

@router.get("/{contract_id}/export-pdf")
async def export_pdf(
    contract_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Contract)
        .options(
            selectinload(Contract.summary),
            selectinload(Contract.clauses)
        )
        .where(
            Contract.id == contract_id,
            Contract.org_id == current_user.org_id
        )
    )

    contract = result.scalar_one_or_none()

    if not contract:
        raise HTTPException(
            status_code=404,
            detail="Contract not found"
        )

    if not contract.summary:
        raise HTTPException(
            status_code=400,
            detail="Contract has not been processed yet"
        )

    os.makedirs("exports", exist_ok=True)

    pdf_path = f"exports/{contract.id}.pdf"

    generate_contract_pdf(
        pdf_path,
        contract,
        contract.summary,
        contract.clauses
    )

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"{contract.filename}_report.pdf"
    )
@router.delete("/{contract_id}", status_code=204)
async def delete_contract(
    contract_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Contract).where(
            Contract.id == contract_id,
            Contract.org_id == current_user.org_id
        )
    )
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    # Delete file from disk
    if os.path.exists(contract.file_path):
        os.remove(contract.file_path)

    await db.delete(contract)
    await db.commit()
