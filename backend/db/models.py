"""
db/models.py — SQLAlchemy ORM models for SmartClause
Multi-tenant: every row is scoped to an organization.
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    String, Boolean, DateTime, ForeignKey,
    Integer, Float, Text, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from db.database import Base
import enum


class PlanType(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"


class ContractStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


def gen_uuid():
    return str(uuid.uuid4())


# ── Organization ─────────────────────────────────────────
class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[PlanType] = mapped_column(SAEnum(PlanType), default=PlanType.FREE)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    users: Mapped[list["User"]] = relationship("User", back_populates="organization")
    contracts: Mapped[list["Contract"]] = relationship("Contract", back_populates="organization")


# ── User ─────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)  # None for OAuth users
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.MEMBER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    google_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    organization: Mapped["Organization"] = relationship("Organization", back_populates="users")
    contracts: Mapped[list["Contract"]] = relationship("Contract", back_populates="user")


# ── Contract ─────────────────────────────────────────────
class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[ContractStatus] = mapped_column(SAEnum(ContractStatus), default=ContractStatus.UPLOADED)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="contracts")
    user: Mapped["User"] = relationship("User", back_populates="contracts")
    clauses: Mapped[list["Clause"]] = relationship("Clause", back_populates="contract", cascade="all, delete-orphan")
    summary: Mapped["ExtractionSummary | None"] = relationship("ExtractionSummary", back_populates="contract", uselist=False, cascade="all, delete-orphan")


# ── Clause ───────────────────────────────────────────────
class Clause(Base):
    __tablename__ = "clauses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    contract_id: Mapped[str] = mapped_column(String(36), ForeignKey("contracts.id"), nullable=False)
    clause_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    asc606_step: Mapped[int | None] = mapped_column(Integer, nullable=True)
    asc606_relevance: Mapped[str | None] = mapped_column(Text, nullable=True)
    section: Mapped[str] = mapped_column(String(500), nullable=False)
    parent_article: Mapped[str | None] = mapped_column(String(500), nullable=True)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    extracted_values: Mapped[dict] = mapped_column(JSONB, default=dict)
    flags: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    contract: Mapped["Contract"] = relationship("Contract", back_populates="clauses")


# ── Extraction Summary ────────────────────────────────────
class ExtractionSummary(Base):
    __tablename__ = "extraction_summaries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    contract_id: Mapped[str] = mapped_column(String(36), ForeignKey("contracts.id"), unique=True, nullable=False)
    total_clauses: Mapped[int] = mapped_column(Integer, default=0)
    total_contract_value_usd: Mapped[float] = mapped_column(Float, default=0.0)
    duration_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    license_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    recognition_pattern: Mapped[str | None] = mapped_column(String(100), nullable=True)
    has_variable_consideration: Mapped[bool] = mapped_column(Boolean, default=False)
    has_refund_rights: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_renewal: Mapped[bool] = mapped_column(Boolean, default=False)
    average_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    clauses_by_type: Mapped[dict] = mapped_column(JSONB, default=dict)
    risk_flags: Mapped[list] = mapped_column(JSONB, default=list)
    extractor_coverage: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    contract: Mapped["Contract"] = relationship("Contract", back_populates="summary")
