"""
Authentication endpoints — register, login, refresh, logout using Supabase Auth.
"""

import uuid
import httpx
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, field_validator
from loguru import logger

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.postgres_models import User

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Full name must be at least 2 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    full_name: str
    role: str


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user account via Supabase Auth GoTrue."""
    async with httpx.AsyncClient() as client:
        headers = {"apiKey": settings.SUPABASE_ANON_KEY, "Content-Type": "application/json"}
        signup_data = {
            "email": body.email,
            "password": body.password,
            "data": {"full_name": body.full_name}
        }
        resp = await client.post(
            f"{settings.SUPABASE_URL}/auth/v1/signup",
            json=signup_data,
            headers=headers
        )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=resp.status_code,
                detail=resp.json().get("msg", "Registration failed via Supabase Auth.")
            )
        
        resp_data = resp.json()
        user_info = resp_data.get("user", {})
        user_id = user_info.get("id")
        
        session = resp_data.get("session")
        if not session:
            # If autologin didn't trigger immediately, log in to get session
            login_resp = await client.post(
                f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password",
                json={"email": body.email, "password": body.password},
                headers=headers
            )
            if login_resp.status_code == 200:
                session = login_resp.json()
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Registration succeeded, but verification is required."
                )

        access_token = session["access_token"]
        refresh_token = session["refresh_token"]

        # Sync user in public PostgreSQL database
        from sqlalchemy import select
        res = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = res.scalar_one_or_none()
        if not user:
            user = User(
                id=uuid.UUID(user_id),
                email=body.email,
                full_name=body.full_name,
                role="user",
                is_active=True,
                is_verified=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        logger.bind(user_id=user_id).info("User registered via Supabase Auth")
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user_id,
            email=body.email,
            full_name=body.full_name,
            role="user"
        )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate user with Supabase Auth password grant and return session."""
    async with httpx.AsyncClient() as client:
        headers = {"apiKey": settings.SUPABASE_ANON_KEY, "Content-Type": "application/json"}
        login_data = {
            "email": body.email,
            "password": body.password
        }
        resp = await client.post(
            f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password",
            json=login_data,
            headers=headers
        )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=resp.json().get("error_description", "Invalid email or password.")
            )
        
        resp_data = resp.json()
        access_token = resp_data["access_token"]
        refresh_token = resp_data["refresh_token"]
        user_info = resp_data["user"]
        user_id = user_info["id"]
        email = user_info["email"]
        full_name = user_info.get("user_metadata", {}).get("full_name", "Supabase User")

        # Sync user in public PostgreSQL database
        from sqlalchemy import select
        res = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = res.scalar_one_or_none()
        if not user:
            user = User(
                id=uuid.UUID(user_id),
                email=email,
                full_name=full_name,
                role="user",
                is_active=True,
                is_verified=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        logger.bind(user_id=user_id).info("User logged in via Supabase Auth")
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user_id,
            email=email,
            full_name=full_name,
            role=user.role
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Refresh session token via Supabase Auth GoTrue."""
    async with httpx.AsyncClient() as client:
        headers = {"apiKey": settings.SUPABASE_ANON_KEY, "Content-Type": "application/json"}
        refresh_data = {
            "refresh_token": body.refresh_token
        }
        resp = await client.post(
            f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=refresh_token",
            json=refresh_data,
            headers=headers
        )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token."
            )
        
        resp_data = resp.json()
        access_token = resp_data["access_token"]
        new_refresh_token = resp_data["refresh_token"]
        user_info = resp_data["user"]
        user_id = user_info["id"]
        email = user_info["email"]
        full_name = user_info.get("user_metadata", {}).get("full_name", "Supabase User")

        # Fetch synced user role
        from sqlalchemy import select
        res = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = res.scalar_one_or_none()
        role = user.role if user else "user"

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            user_id=user_id,
            email=email,
            full_name=full_name,
            role=role
        )


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Get the currently authenticated user's profile."""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "headline": current_user.headline,
        "location": current_user.location,
        "avatar_url": current_user.avatar_url,
        "is_verified": current_user.is_verified,
        "created_at": current_user.created_at.isoformat(),
    }
