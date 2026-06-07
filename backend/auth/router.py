"""
auth/router.py
--------------
All authentication endpoints:
  POST /auth/register     - email+password signup
  POST /auth/login        - email+password login
  POST /auth/refresh      - refresh access token
  GET  /auth/me           - get current user
  GET  /auth/google       - redirect to Google OAuth
  GET  /auth/google/callback - handle Google OAuth callback
"""
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext
from datetime import datetime, timezone
import uuid

from db.database import get_db, settings
from db.models import User, Organization, UserRole, PlanType
from db.schemas import RegisterRequest, LoginRequest, TokenResponse, UserResponse, RefreshRequest
from auth.dependencies import (
    create_access_token, create_refresh_token,
    decode_token, get_current_user
)

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def gen_id(): return str(uuid.uuid4())


# ── Register ─────────────────────────────────────────────
@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    # Create org first
    org = Organization(id=gen_id(), name=body.org_name, plan=PlanType.FREE)
    db.add(org)
    await db.flush()

    user = User(
        id=gen_id(),
        org_id=org.id,
        email=body.email,
        hashed_password=pwd_ctx.hash(body.password),
        full_name=body.full_name,
        role=UserRole.ADMIN,   # First user of an org is always admin
        is_verified=False,
    )
    db.add(user)
    await db.flush()

    return TokenResponse(
        access_token=create_access_token(user.id, org.id),
        refresh_token=create_refresh_token(user.id),
        user=UserResponse.model_validate(user),
    )


# ── Login ─────────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email, User.is_active == True))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password or not pwd_ctx.verify(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user.last_login = datetime.now()

    return TokenResponse(
        access_token=create_access_token(user.id, user.org_id),
        refresh_token=create_refresh_token(user.id),
        user=UserResponse.model_validate(user),
    )


# ── Refresh Token ─────────────────────────────────────────
@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    result = await db.execute(select(User).where(User.id == payload["sub"], User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return TokenResponse(
        access_token=create_access_token(user.id, user.org_id),
        refresh_token=create_refresh_token(user.id),
        user=UserResponse.model_validate(user),
    )


# ── Me ────────────────────────────────────────────────────
@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


# ── Google OAuth ──────────────────────────────────────────
@router.get("/google")
async def google_login():
    params = (
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=openid email profile"
        f"&access_type=offline"
    )
    return RedirectResponse(GOOGLE_AUTH_URL + params)


@router.get("/google/callback")
async def google_callback(code: str, db: AsyncSession = Depends(get_db)):
    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_res = await client.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        })
        if token_res.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange Google code")

        google_token = token_res.json()["access_token"]
        user_res = await client.get(GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {google_token}"})
        google_user = user_res.json()

    google_id = google_user["sub"]
    email = google_user["email"]
    full_name = google_user.get("name", "")
    avatar_url = google_user.get("picture", "")

    # Find or create user
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if not user:
        result2 = await db.execute(select(User).where(User.email == email))
        user = result2.scalar_one_or_none()

    if not user:
        org = Organization(id=gen_id(), name=f"{full_name}'s Organization", plan=PlanType.FREE)
        db.add(org)
        await db.flush()

        user = User(
            id=gen_id(),
            org_id=org.id,
            email=email,
            full_name=full_name,
            avatar_url=avatar_url,
            google_id=google_id,
            role=UserRole.ADMIN,
            is_verified=True,
        )
        db.add(user)
        await db.flush()
    else:
        user.google_id = google_id
        user.avatar_url = avatar_url
        user.last_login = datetime.now()

    access_token = create_access_token(user.id, user.org_id)
    refresh_token = create_refresh_token(user.id)

    # Redirect to frontend with tokens in URL fragment
    return RedirectResponse(
        f"{settings.FRONTEND_URL}/auth/callback"
        f"#access_token={access_token}&refresh_token={refresh_token}"
    )
