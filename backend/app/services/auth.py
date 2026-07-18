"""Authentication and session lifecycle services."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import (
    generate_csrf_token,
    generate_session_token,
    hash_password,
    hash_token,
    needs_rehash,
    verify_password,
)
from app.models.session import Session
from app.models.user import User


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuthService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    async def user_count(self) -> int:
        result = await self.db.scalar(select(func.count()).select_from(User))
        return int(result or 0)

    async def bootstrap_required(self) -> bool:
        return await self.user_count() == 0

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self.db.scalar(
            select(User).where(User.email == email.lower().strip())
        )
        return result

    async def bootstrap(
        self, *, email: str, password: str, display_name: str
    ) -> User:
        if not await self.bootstrap_required():
            raise AppError(
                code="bootstrap_unavailable",
                message="Owner account already exists. Use login instead.",
                status_code=409,
            )
        user = User(
            email=email.lower().strip(),
            display_name=display_name.strip(),
            password_hash=hash_password(password),
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def authenticate(self, *, email: str, password: str) -> User:
        user = await self.get_user_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise AppError(
                code="invalid_credentials",
                message="Invalid email or password",
                status_code=401,
            )
        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
            await self.db.commit()
            await self.db.refresh(user)
        return user

    async def create_session(
        self,
        user: User,
        *,
        user_agent: str | None,
        ip_address: str | None,
    ) -> tuple[Session, str]:
        raw_token = generate_session_token()
        session = Session(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            csrf_token=generate_csrf_token(),
            user_agent=(user_agent or "")[:512] or None,
            ip_address=ip_address,
            expires_at=_utcnow()
            + timedelta(minutes=self.settings.session_ttl_minutes),
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session, raw_token

    async def get_active_session(self, raw_token: str) -> Session | None:
        token_hash = hash_token(raw_token)
        session = await self.db.scalar(
            select(Session).where(Session.token_hash == token_hash)
        )
        if session is None or not session.is_active:
            return None
        session.last_seen_at = _utcnow()
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def revoke_session(self, session: Session) -> None:
        session.revoked_at = _utcnow()
        await self.db.commit()

    async def change_password(
        self, user: User, *, current_password: str, new_password: str
    ) -> None:
        if not verify_password(current_password, user.password_hash):
            raise AppError(
                code="invalid_credentials",
                message="Current password is incorrect",
                status_code=401,
            )
        if current_password == new_password:
            raise AppError(
                code="password_unchanged",
                message="New password must be different from the current password",
                status_code=400,
            )
        user.password_hash = hash_password(new_password)
        await self.db.execute(
            update(Session)
            .where(Session.user_id == user.id, Session.revoked_at.is_(None))
            .values(revoked_at=_utcnow())
        )
        await self.db.commit()
