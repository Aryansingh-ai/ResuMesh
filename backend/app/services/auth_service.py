from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request

from app.models.user import User
from app.models.cover_letter import AuditLog
from app.repositories.user import UserRepository
from app.repositories.cover_letter import AuditLogRepository
from app.core.security import hash_password, verify_password


class AuthService:
    """Service layer for authentication and session logging."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.audit_repo = AuditLogRepository(db)

    async def register_user(
        self, email: str, password: str, full_name: str, request: Request
    ) -> User:
        """Register a new user and log the action."""
        user = User(
            email=email.lower(),
            hashed_password=hash_password(password),
            full_name=full_name,
        )
        await self.user_repo.create(user)

        # Create audit log
        audit = AuditLog(
            user_id=user.id,
            action="user.register",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            success=True,
        )
        await self.audit_repo.create(audit)
        return user

    async def authenticate_user(
        self, email: str, password: str, request: Request
    ) -> Optional[User]:
        """Authenticate user credentials and log login success or failure."""
        user = await self.user_repo.get_by_email(email.lower())
        if not user or not verify_password(password, user.hashed_password):
            # Log failed login attempt
            audit = AuditLog(
                user_id=user.id if user else None,
                action="user.login.failed",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                success=False,
                meta_data={"email_attempted": email.lower()},
            )
            await self.audit_repo.create(audit)
            return None

        if not user.is_active:
            return None

        # Update last login time
        user.last_login_at = datetime.now(timezone.utc)
        self.db.add(user)

        # Log successful login
        audit = AuditLog(
            user_id=user.id,
            action="user.login",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            success=True,
        )
        await self.audit_repo.create(audit)
        return user
