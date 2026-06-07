"""
db/schemas.py — Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional, Any
import re


# ── Auth ─────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    org_name: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain an uppercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain a number")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class RefreshRequest(BaseModel):
    refresh_token: str


# ── User ─────────────────────────────────────────────────
class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    role: str
    org_id: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Organization ─────────────────────────────────────────
class OrgResponse(BaseModel):
    id: str
    name: str
    plan: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Contract ─────────────────────────────────────────────
class ContractResponse(BaseModel):
    id: str
    filename: str
    status: str
    file_size_bytes: int
    created_at: datetime
    processed_at: Optional[datetime]
    user_id: str

    class Config:
        from_attributes = True


class ContractDetailResponse(ContractResponse):
    summary: Optional["SummaryResponse"]
    clauses: list["ClauseResponse"]


# ── Clause ───────────────────────────────────────────────
class ClauseResponse(BaseModel):
    id: str
    clause_type: str
    asc606_step: Optional[int]
    asc606_relevance: Optional[str]
    section: str
    parent_article: Optional[str]
    extracted_text: str
    confidence: float
    extracted_values: dict
    flags: list

    class Config:
        from_attributes = True


# ── Summary ──────────────────────────────────────────────
class SummaryResponse(BaseModel):
    total_clauses: int
    total_contract_value_usd: float
    duration_months: Optional[int]
    license_type: Optional[str]
    recognition_pattern: Optional[str]
    has_variable_consideration: bool
    has_refund_rights: bool
    auto_renewal: bool
    average_confidence: float
    clauses_by_type: dict
    risk_flags: list
    extractor_coverage: dict

    class Config:
        from_attributes = True


# Update forward refs
TokenResponse.model_rebuild()
ContractDetailResponse.model_rebuild()
