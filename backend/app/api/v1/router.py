"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    diagnostics,
    health,
    jobs,
    masks,
    projects,
    settings,
    smart_edit,
    uploads,
    videos,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(uploads.router)
api_router.include_router(videos.router)
api_router.include_router(masks.router)
api_router.include_router(jobs.router)
api_router.include_router(settings.router)
api_router.include_router(smart_edit.router)
api_router.include_router(projects.router)
api_router.include_router(diagnostics.router)
