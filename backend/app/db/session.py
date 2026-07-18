"""Async database engine and session factory."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.db.base import Base

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine, _session_factory
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.debug and settings.app_env == "development",
            connect_args={"check_same_thread": False}
            if settings.database_url.startswith("sqlite")
            else {},
        )
        _session_factory = async_sessionmaker(
            bind=_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    get_engine()
    assert _session_factory is not None
    return _session_factory


def _sqlite_add_missing_columns(sync_conn) -> None:  # noqa: ANN001
    """Best-effort additive migrations for SQLite (keeps older DBs working)."""
    from sqlalchemy import inspect, text

    inspector = inspect(sync_conn)
    tables = set(inspector.get_table_names())
    if "processing_jobs" in tables:
        existing = {col["name"] for col in inspector.get_columns("processing_jobs")}
        alters = []
        if "strategy_used" not in existing:
            alters.append(
                "ALTER TABLE processing_jobs ADD COLUMN strategy_used VARCHAR(64)"
            )
        if "cancel_requested" not in existing:
            alters.append(
                "ALTER TABLE processing_jobs ADD COLUMN cancel_requested BOOLEAN DEFAULT 0"
            )
        if "pause_requested" not in existing:
            alters.append(
                "ALTER TABLE processing_jobs ADD COLUMN pause_requested BOOLEAN DEFAULT 0"
            )
        for stmt in alters:
            sync_conn.execute(text(stmt))


async def init_db() -> None:
    from app import models  # noqa: F401

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if engine.dialect.name == "sqlite":
            await conn.run_sync(_sqlite_add_missing_columns)


async def get_db() -> AsyncIterator[AsyncSession]:
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def dispose_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
