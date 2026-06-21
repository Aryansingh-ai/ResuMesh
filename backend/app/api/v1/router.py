"""API v1 router — aggregates all endpoint modules."""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth, resumes, jobs, matching,
    cover_letters, rag, applications,
    feedback, users, analytics, admin,
)

api_router = APIRouter()

api_router.include_router(auth.router,          prefix="/auth",         tags=["Auth"])
api_router.include_router(users.router,         prefix="/users",        tags=["Users"])
api_router.include_router(resumes.router,       prefix="/resumes",      tags=["Resumes"])
api_router.include_router(jobs.router,          prefix="/jobs",         tags=["Jobs"])
api_router.include_router(matching.router,      prefix="/matching",     tags=["Matching"])
api_router.include_router(cover_letters.router, prefix="/coverletters", tags=["Cover Letters"])
api_router.include_router(rag.router,           prefix="/rag",          tags=["RAG Coach"])
api_router.include_router(applications.router,  prefix="/applications", tags=["Applications"])
api_router.include_router(feedback.router,      prefix="/feedback",     tags=["Feedback"])
api_router.include_router(analytics.router,     prefix="/analytics",    tags=["Analytics"])
api_router.include_router(admin.router,         prefix="/admin",        tags=["Admin"])
