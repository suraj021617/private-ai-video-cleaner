"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
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

    cors_origins: str = "http://localhost:3000"

    database_url: str = "sqlite+aiosqlite:///./data/app.db"

    storage_root: Path = Path("../storage")
    max_upload_bytes: int = 512 * 1024 * 1024
    upload_chunk_size: int = 5 * 1024 * 1024

    secret_key: str = Field(
        default="change-me-in-production-use-long-random-string",
        min_length=32,
    )
    session_cookie_name: str = "pavc_session"
    csrf_cookie_name: str = "pavc_csrf"
    session_ttl_minutes: int = 60 * 24 * 7
    cookie_secure: bool = False
    cookie_samesite: str = "lax"

    # Auth rate limiting (in-memory; per-process)
    auth_rate_limit_attempts: int = 10
    auth_rate_limit_window_seconds: int = 300

    allowed_video_extensions: str = "mp4,mov,m4v,webm,mkv"
    allowed_video_mime_types: str = (
        "video/mp4,video/quicktime,video/webm,video/x-matroska,application/octet-stream"
    )

    # LaMa / AI processing settings
    lama_model_dir: Path = Path("../models/lama")
    lama_model_url: str = (
        "https://github.com/enesmsahin/simple-lama-inpainting/releases/download/v0.1.0/big-lama.pt"
    )
    lama_prefer_gpu: bool = True
    lama_padding: int = 64
    lama_blend_strength: float = 1.0
    lama_feather_radius: int = 12
    lama_cpu_threads: int = 0  # 0 = torch default
    processing_temp_dir: Path | None = None
    max_concurrent_jobs: int = 1
    # Lite mode: no expectation of torch/LaMa; classic strategies preferred in UI
    lite_mode: bool = False

    @field_validator("cookie_samesite")
    @classmethod
    def validate_samesite(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in {"lax", "strict", "none"}:
            raise ValueError("cookie_samesite must be lax, strict, or none")
        return normalized

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
        if self.processing_temp_dir is not None:
            return Path(self.processing_temp_dir)
        return self.storage_root / "temp"

    @property
    def extension_allowlist(self) -> set[str]:
        return {
            e.strip().lower().lstrip(".")
            for e in self.allowed_video_extensions.split(",")
            if e.strip()
        }

    @property
    def mime_allowlist(self) -> set[str]:
        return {
            m.strip().lower()
            for m in self.allowed_video_mime_types.split(",")
            if m.strip()
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
