"""Resumable LaMa checkpoint download with progress callbacks."""

from __future__ import annotations

import logging
import os
import tempfile
import urllib.request
from collections.abc import Callable
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_LAMA_URL = os.environ.get(
    "LAMA_MODEL_URL",
    "https://github.com/enesmsahin/simple-lama-inpainting/releases/download/v0.1.0/big-lama.pt",
)

ProgressCallback = Callable[[int, int | None], None]


class ResumeDownloadError(RuntimeError):
    pass


def download_file(
    url: str,
    dest: Path,
    *,
    progress: ProgressCallback | None = None,
    chunk_size: int = 1024 * 1024,
) -> Path:
    """
    Download `url` to `dest` with resume support via HTTP Range.

    Writes to `dest.with_suffix(dest.suffix + '.part')` until complete.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    existing = part.stat().st_size if part.exists() else 0

    request = urllib.request.Request(url, method="GET")
    request.add_header("User-Agent", "PrivateAIVideoCleaner/0.5")
    if existing > 0:
        request.add_header("Range", f"bytes={existing}-")

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            status = getattr(response, "status", 200)
            # 200 = full body, 206 = partial
            if status == 200 and existing > 0:
                # Server ignored Range — restart
                existing = 0
                part.unlink(missing_ok=True)

            total_header = response.headers.get("Content-Length")
            content_range = response.headers.get("Content-Range")
            total: int | None = None
            if content_range and "/" in content_range:
                try:
                    total = int(content_range.rsplit("/", 1)[-1])
                except ValueError:
                    total = None
            elif total_header:
                try:
                    total = int(total_header) + (existing if status == 206 else 0)
                except ValueError:
                    total = None

            mode = "ab" if existing > 0 and status == 206 else "wb"
            downloaded = existing if mode == "ab" else 0
            with part.open(mode) as handle:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    handle.write(chunk)
                    downloaded += len(chunk)
                    if progress:
                        progress(downloaded, total)
    except Exception as exc:  # noqa: BLE001
        raise ResumeDownloadError(f"Failed to download LaMa model: {exc}") from exc

    # Atomic replace
    tmp_final = dest.with_suffix(dest.suffix + ".tmp")
    if tmp_final.exists():
        tmp_final.unlink()
    part.replace(dest)
    logger.info("LaMa checkpoint ready at %s", dest)
    return dest


def ensure_lama_checkpoint(
    model_dir: Path,
    *,
    url: str = DEFAULT_LAMA_URL,
    filename: str = "big-lama.pt",
    progress: ProgressCallback | None = None,
) -> Path:
    """Return local checkpoint path, downloading if missing."""
    model_dir.mkdir(parents=True, exist_ok=True)
    dest = model_dir / filename
    if dest.is_file() and dest.stat().st_size > 1_000_000:
        if progress:
            size = dest.stat().st_size
            progress(size, size)
        return dest
    return download_file(url, dest, progress=progress)
