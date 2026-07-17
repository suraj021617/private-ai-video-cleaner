"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.endpoints import health

api_router = APIRouter()
api_router.include_router(health.router)

# Future routers (Phases 3–8):
# api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
# api_router.include_router(videos.router, prefix="/videos", tags=["videos"])
# api_router.include_router(selections.router, prefix="/selections", tags=["selections"])
# api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
# api_router.include_router(exports.router, prefix="/exports", tags=["exports"])
