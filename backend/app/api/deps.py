"""FastAPI dependencies: DB, auth, CSRF."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from starlette.responses import Response as StarletteResponse

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.security import csrf_tokens_match
from app.db.session import get_db
from app.models.session import Session
from app.models.user import User
from app.services.auth import AuthService


SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


@dataclass
class AuthContext:
    user: User
    session: Session
    csrf_token: str


def get_auth_service(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    return AuthService(db, settings)


async def get_optional_auth(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthContext | None:
    raw = request.cookies.get(settings.session_cookie_name)
    if not raw:
        return None
    session = await auth_service.get_active_session(raw)
    if session is None:
        return None
    user = await db.scalar(select(User).where(User.id == session.user_id))
    if user is None:
        return None
    return AuthContext(user=user, session=session, csrf_token=session.csrf_token)


async def require_auth(
    request: Request,
    auth: AuthContext | None = Depends(get_optional_auth),
    settings: Settings = Depends(get_settings),
) -> AuthContext:
    if auth is None:
        raise AppError(
            code="unauthorized",
            message="Authentication required",
            status_code=401,
        )
    if request.method not in SAFE_METHODS:
        provided = request.headers.get("X-CSRF-Token")
        if not csrf_tokens_match(auth.csrf_token, provided):
            raise AppError(
                code="csrf_failed",
                message="CSRF token missing or invalid",
                status_code=403,
            )
    return auth


def set_auth_cookies(
    response: Response | StarletteResponse,
    *,
    settings: Settings,
    session_token: str,
    csrf_token: str,
) -> None:
    samesite = settings.cookie_samesite
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=samesite,  # type: ignore[arg-type]
        max_age=settings.session_ttl_minutes * 60,
        path="/",
    )
    # CSRF cookie is readable by JS so the SPA can mirror it into X-CSRF-Token
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=samesite,  # type: ignore[arg-type]
        max_age=settings.session_ttl_minutes * 60,
        path="/",
    )


def clear_auth_cookies(response: Response, settings: Settings) -> None:
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")


def client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    if request.client:
        return request.client.host
    return None
