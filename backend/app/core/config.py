"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the API."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Private AI Video Cleaner"
    app_env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    # CORS — frontend origin(s); tighten in production
    cors_origins: str = "http://localhost:3000"

    # Local media roots (relative to repo root when running from backend/)
    storage_root: Path = Path("../storage")
    max_upload_bytes: int = 512 * 1024 * 1024  # 512 MB soft for Phase 4

    # Auth placeholders (wired in Phase 3)
    secret_key: str = "change-me-in-production-use-long-random-string"
    access_token_expire_minutes: int = 60 * 24

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def uploads_dir(self) -> Path:
        return self.storage_root / "uploads"

    @property
    def processed_dir(self) -> Path:
        return self.storage_root / "processed"

    @property
    def temp_dir(self) -> Path:
        return self.storage_root / "temp"


@lru_cache
def get_settings() -> Settings:
    return Settings()
