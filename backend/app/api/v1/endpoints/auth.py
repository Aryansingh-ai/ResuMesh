"""
Authentication endpoints — register, login, refresh, logout.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, field_validator
import structlog

from app.core.database import get_db
from app.core.security import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, decode_token, get_current_user,
)
from app.models.user import User
from app.models.cover_letter import AuditLog
from app.services.user_service import UserService

router = APIRouter()
logger = structlog.get_logger(__name__)


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
async def register(body: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    user_service = UserService(db)

    # Check if email exists
    existing = await user_service.get_by_email(body.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    # Create user
    user = User(
        email=body.email.lower(),
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
    )
    db.add(user)
    await db.flush()

    # Audit log
    db.add(AuditLog(
        user_id=user.id,
        action="user.register",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        success=True,
    ))

    await db.commit()
    await db.refresh(user)

    access_token = create_access_token({"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    logger.info("User registered", user_id=str(user.id), email=user.email)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return tokens."""
    user_service = UserService(db)

    user = await user_service.get_by_email(body.email.lower())
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled. Contact support.",
        )

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)

    db.add(AuditLog(
        user_id=user.id,
        action="user.login",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        success=True,
    ))

    await db.commit()

    access_token = create_access_token({"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    logger.info("User logged in", user_id=str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Issue a new access token using a valid refresh token."""
    payload = decode_token(body.refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. Expected refresh token.",
        )

    user_service = UserService(db)
    user = await user_service.get_by_id(payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    access_token = create_access_token({"sub": str(user.id), "email": user.email})
    new_refresh_token = create_refresh_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        user_id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
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
