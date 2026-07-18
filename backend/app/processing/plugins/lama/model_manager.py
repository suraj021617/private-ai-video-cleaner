"""LaMa model lifecycle: download, load, device selection, OOM fallback."""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

from app.processing.plugins.lama.download import (
    DEFAULT_LAMA_URL,
    ensure_lama_checkpoint,
)

logger = logging.getLogger(__name__)


class LamaModelManager:
    """Thread-safe singleton-style manager for the TorchScript LaMa model."""

    def __init__(
        self,
        model_dir: Path,
        *,
        prefer_gpu: bool = True,
        model_url: str = DEFAULT_LAMA_URL,
    ) -> None:
        self.model_dir = Path(model_dir)
        self.prefer_gpu = prefer_gpu
        self.model_url = model_url
        self._lock = threading.RLock()
        self._model: Any = None
        self._device: str = "cpu"
        self._checkpoint: Path | None = None
        self._download_bytes: int = 0
        self._download_total: int | None = None
        self._status: str = "idle"
        self._error: str | None = None

    @property
    def status(self) -> dict[str, Any]:
        return {
            "status": self._status,
            "device": self._device,
            "model_loaded": self._model is not None,
            "checkpoint": str(self._checkpoint) if self._checkpoint else None,
            "download_bytes": self._download_bytes,
            "download_total": self._download_total,
            "error": self._error,
            "cuda_available": self._cuda_available(),
        }

    def _cuda_available(self) -> bool:
        try:
            import torch

            return bool(torch.cuda.is_available())
        except Exception:  # noqa: BLE001
            return False

    def select_device(self, prefer_gpu: bool | None = None) -> str:
        prefer = self.prefer_gpu if prefer_gpu is None else prefer_gpu
        if prefer and self._cuda_available():
            return "cuda"
        return "cpu"

    def ensure_model(self, prefer_gpu: bool | None = None) -> Any:
        with self._lock:
            device = self.select_device(prefer_gpu)
            if self._model is not None and self._device == device:
                return self._model

            self._status = "downloading"
            self._error = None

            def _progress(done: int, total: int | None) -> None:
                self._download_bytes = done
                self._download_total = total
                self._status = "downloading"

            try:
                checkpoint = ensure_lama_checkpoint(
                    self.model_dir,
                    url=self.model_url,
                    progress=_progress,
                )
                self._checkpoint = checkpoint
                self._status = "loading"
                import torch

                model = torch.jit.load(str(checkpoint), map_location=device)
                model.eval()
                model.to(device)
                self._model = model
                self._device = device
                self._status = "ready"
                logger.info("LaMa model loaded on %s from %s", device, checkpoint)
                return self._model
            except Exception as exc:  # noqa: BLE001
                self._status = "error"
                self._error = str(exc)
                self._model = None
                raise

    def predict(self, image_tensor, mask_tensor):  # noqa: ANN001
        import torch

        with self._lock:
            if self._model is None:
                raise RuntimeError("LaMa model is not loaded")
            try:
                with torch.inference_mode():
                    return self._model(image_tensor, mask_tensor)
            except RuntimeError as exc:
                message = str(exc).lower()
                if "out of memory" in message and self._device == "cuda":
                    logger.warning("CUDA OOM — falling back to CPU for LaMa")
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    self._model = None
                    self._device = "cpu"
                    self.ensure_model(prefer_gpu=False)
                    image_cpu = image_tensor.to("cpu")
                    mask_cpu = mask_tensor.to("cpu")
                    with torch.inference_mode():
                        return self._model(image_cpu, mask_cpu)
                raise

    def unload(self) -> None:
        with self._lock:
            self._model = None
            self._status = "idle"
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:  # noqa: BLE001
                pass


_MANAGER: LamaModelManager | None = None
_MANAGER_LOCK = threading.Lock()


def get_model_manager(model_dir: Path, *, prefer_gpu: bool = True) -> LamaModelManager:
    global _MANAGER
    with _MANAGER_LOCK:
        if _MANAGER is None or Path(_MANAGER.model_dir) != Path(model_dir):
            _MANAGER = LamaModelManager(model_dir, prefer_gpu=prefer_gpu)
        else:
            _MANAGER.prefer_gpu = prefer_gpu
        return _MANAGER
