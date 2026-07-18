"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from app.api.deps import (
    AuthContext,
    clear_auth_cookies,
    client_ip,
    get_auth_service,
    get_optional_auth,
    require_auth,
    set_auth_cookies,
)
from app.core.config import Settings, get_settings
from app.core.rate_limit import get_auth_rate_limiter
from app.schemas.auth import (
    AuthResponse,
    AuthStatusResponse,
    BootstrapRequest,
    ChangePasswordRequest,
    LoginRequest,
    UserOut,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/status", response_model=AuthStatusResponse)
async def auth_status(
    auth: AuthContext | None = Depends(get_optional_auth),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthStatusResponse:
    return AuthStatusResponse(
        bootstrap_required=await auth_service.bootstrap_required(),
        authenticated=auth is not None,
    )


@router.post("/bootstrap", response_model=AuthResponse)
async def bootstrap(
    payload: BootstrapRequest,
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    limiter = get_auth_rate_limiter(
        settings.auth_rate_limit_attempts,
        settings.auth_rate_limit_window_seconds,
    )
    limiter.check(f"bootstrap:{client_ip(request) or 'unknown'}")

    user = await auth_service.bootstrap(
        email=str(payload.email),
        password=payload.password,
        display_name=payload.display_name,
    )
    session, raw_token = await auth_service.create_session(
        user,
        user_agent=request.headers.get("User-Agent"),
        ip_address=client_ip(request),
    )
    set_auth_cookies(
        response,
        settings=settings,
        session_token=raw_token,
        csrf_token=session.csrf_token,
    )
    return AuthResponse(user=UserOut.model_validate(user), csrf_token=session.csrf_token)


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    limiter = get_auth_rate_limiter(
        settings.auth_rate_limit_attempts,
        settings.auth_rate_limit_window_seconds,
    )
    limiter.check(f"login:{(client_ip(request) or 'unknown')}:{payload.email.lower()}")

    user = await auth_service.authenticate(
        email=str(payload.email),
        password=payload.password,
    )
    session, raw_token = await auth_service.create_session(
        user,
        user_agent=request.headers.get("User-Agent"),
        ip_address=client_ip(request),
    )
    set_auth_cookies(
        response,
        settings=settings,
        session_token=raw_token,
        csrf_token=session.csrf_token,
    )
    return AuthResponse(user=UserOut.model_validate(user), csrf_token=session.csrf_token)


@router.post("/logout", status_code=204, response_model=None)
async def logout(
    response: Response,
    auth: AuthContext = Depends(require_auth),
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> None:
    await auth_service.revoke_session(auth.session)
    clear_auth_cookies(response, settings)


@router.get("/me", response_model=AuthResponse)
async def me(auth: AuthContext = Depends(require_auth)) -> AuthResponse:
    return AuthResponse(
        user=UserOut.model_validate(auth.user),
        csrf_token=auth.csrf_token,
    )


@router.post("/change-password", status_code=204, response_model=None)
async def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    auth: AuthContext = Depends(require_auth),
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> None:
    await auth_service.change_password(
        auth.user,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    clear_auth_cookies(response, settings)
