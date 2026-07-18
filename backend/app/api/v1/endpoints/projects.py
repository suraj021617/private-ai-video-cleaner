"""Project save/restore API."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, require_auth
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.session import get_db
from app.models.project import Project, ProjectService, default_project_payload
from app.models.video import Video
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectOut,
    ProjectSummaryOut,
    ProjectUpdateRequest,
)

router = APIRouter(tags=["projects"])


def _to_summary(project: Project) -> ProjectSummaryOut:
    return ProjectSummaryOut(
        id=project.id,
        name=project.name,
        video_id=project.video_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def _to_out(project: Project) -> ProjectOut:
    try:
        payload = json.loads(project.payload_json or "{}")
    except json.JSONDecodeError:
        payload = {}
    return ProjectOut(
        id=project.id,
        name=project.name,
        video_id=project.video_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        payload=payload,
    )


@router.get("/projects", response_model=ProjectListResponse)
async def list_projects(
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ProjectListResponse:
    rows = await db.scalars(
        select(Project)
        .where(Project.owner_id == auth.user.id)
        .order_by(Project.updated_at.desc())
    )
    items = [_to_summary(row) for row in rows]
    return ProjectListResponse(items=items, total=len(items))


@router.post("/projects", response_model=ProjectOut)
async def create_project(
    body: ProjectCreateRequest,
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ProjectOut:
    if body.video_id:
        video = await db.scalar(select(Video).where(Video.id == body.video_id))
        if video is None or video.owner_id != auth.user.id:
            raise AppError(
                code="video_not_found",
                message="Video not found",
                status_code=404,
            )
    payload = body.payload or default_project_payload(body.video_id)
    if body.video_id and not payload.get("video_id"):
        payload["video_id"] = body.video_id
    project = Project(
        owner_id=auth.user.id,
        video_id=body.video_id,
        name=body.name,
        payload_json=json.dumps(payload),
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    ProjectService(settings).write_sidecar(auth.user.id, project.id, payload)
    return _to_out(project)


@router.get("/projects/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: str,
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ProjectOut:
    project = await db.scalar(select(Project).where(Project.id == project_id))
    if project is None or project.owner_id != auth.user.id:
        raise AppError(code="project_not_found", message="Project not found", status_code=404)
    return _to_out(project)


@router.put("/projects/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: str,
    body: ProjectUpdateRequest,
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ProjectOut:
    project = await db.scalar(select(Project).where(Project.id == project_id))
    if project is None or project.owner_id != auth.user.id:
        raise AppError(code="project_not_found", message="Project not found", status_code=404)
    if body.name is not None:
        project.name = body.name
    if body.video_id is not None:
        video = await db.scalar(select(Video).where(Video.id == body.video_id))
        if video is None or video.owner_id != auth.user.id:
            raise AppError(code="video_not_found", message="Video not found", status_code=404)
        project.video_id = body.video_id
    if body.payload is not None:
        project.payload_json = json.dumps(body.payload)
        ProjectService(settings).write_sidecar(auth.user.id, project.id, body.payload)
    await db.commit()
    await db.refresh(project)
    return _to_out(project)


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    project = await db.scalar(select(Project).where(Project.id == project_id))
    if project is None or project.owner_id != auth.user.id:
        raise AppError(code="project_not_found", message="Project not found", status_code=404)
    await db.delete(project)
    await db.commit()
    sidecar = ProjectService(settings).projects_dir(auth.user.id) / f"{project_id}.pavc.json"
    sidecar.unlink(missing_ok=True)
    return {"status": "deleted", "id": project_id}
