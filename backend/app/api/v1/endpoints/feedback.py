"""Feedback, Users, Analytics, and Admin endpoints."""

# feedback.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
import structlog

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.metrics import feedback_collected_total
from app.models.user import User
from app.models.cover_letter import Feedback

router = APIRouter()
logger = structlog.get_logger(__name__)


class FeedbackRequest(BaseModel):
    feedback_type: str
    application_id: Optional[str] = None
    rating: Optional[int] = None
    comment: Optional[str] = None
    metadata: Optional[dict] = None


@router.post("/")
async def submit_feedback(
    body: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit feedback for a match, recommendation, or cover letter."""
    valid_types = {
        "good_match", "bad_match", "useful_recommendation",
        "not_useful_recommendation", "cover_letter_good", "cover_letter_bad",
    }
    if body.feedback_type not in valid_types:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail=f"Invalid feedback_type. Must be one of: {valid_types}")

    import uuid
    feedback = Feedback(
        user_id=current_user.id,
        application_id=uuid.UUID(body.application_id) if body.application_id else None,
        feedback_type=body.feedback_type,
        rating=body.rating,
        comment=body.comment,
        meta_data=body.metadata,
    )
    db.add(feedback)
    await db.commit()

    feedback_collected_total.labels(feedback_type=body.feedback_type).inc()
    logger.info("Feedback submitted", type=body.feedback_type, user_id=str(current_user.id))

    return {"message": "Feedback recorded. Thank you!", "feedback_type": body.feedback_type}
