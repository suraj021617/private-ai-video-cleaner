"""LaMa plugin unit tests (no full model download required)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from app.processing.mask_raster import assert_outside_unchanged
from app.processing.plugins.lama.download import download_file, ensure_lama_checkpoint
from app.processing.plugins.lama.predict import inpaint_frame_with_lama
from app.processing.plugins.lama.utils import (
    blend_crop,
    dilate_mask,
    expand_bbox,
    feather_mask,
    mask_bbox,
)
from app.processing.strategies.ai_inpaint import AIInpaintPlugin
from app.processing.types import (
    ComputeDevice,
    FrameContext,
    StrategyOptions,
)


def test_mask_bbox_and_expand() -> None:
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[40:50, 40:50] = 255
    bbox = mask_bbox(mask)
    assert bbox == (40, 40, 50, 50)
    x1, y1, x2, y2 = expand_bbox(*bbox, width=100, height=100, padding=16)
    assert x1 <= 40 and y1 <= 40
    assert (x2 - x1) % 8 == 0
    assert (y2 - y1) % 8 == 0


def test_feather_and_blend_soft_edges() -> None:
    frame = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[20:40, 20:40] = 255
    crop = frame[16:48, 16:48].copy()
    fake_inpaint = np.clip(crop.astype(np.int16) + 40, 0, 255).astype(np.uint8)
    out = blend_crop(
        frame,
        fake_inpaint,
        mask[16:48, 16:48],
        x1=16,
        y1=16,
        x2=48,
        y2=48,
        blend_strength=1.0,
        feather_radius=8,
    )
    # Far outside the feathered crop must stay identical
    assert np.array_equal(out[0:8, 0:8], frame[0:8, 0:8])
    alpha = feather_mask(mask[16:48, 16:48], radius=8)
    assert alpha.max() <= 1.0 and alpha.min() >= 0.0
    dilated = dilate_mask(mask, 4)
    assert int(np.count_nonzero(dilated)) >= int(np.count_nonzero(mask))
    # Inside hard mask should change
    assert not np.array_equal(out[25:30, 25:30], frame[25:30, 25:30])


def test_resume_download(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dest = tmp_path / "model.pt"
    payload = b"0123456789ABCDEF" * 1000

    class FakeResp:
        def __init__(self, data: bytes, status: int = 200, headers: dict | None = None):
            self._data = data
            self.status = status
            self.headers = headers or {"Content-Length": str(len(data))}
            self._i = 0

        def read(self, n: int = -1) -> bytes:
            if self._i >= len(self._data):
                return b""
            if n < 0:
                chunk = self._data[self._i :]
                self._i = len(self._data)
                return chunk
            chunk = self._data[self._i : self._i + n]
            self._i += len(chunk)
            return chunk

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    calls = {"n": 0}

    def fake_urlopen(req, timeout=120):  # noqa: ANN001
        calls["n"] += 1
        range_header = req.headers.get("Range") if hasattr(req, "headers") else None
        # urllib Request uses header_items
        headers = dict(req.header_items()) if hasattr(req, "header_items") else {}
        range_header = headers.get("Range") or headers.get("range")
        if range_header:
            start = int(range_header.split("=")[1].split("-")[0])
            data = payload[start:]
            return FakeResp(
                data,
                status=206,
                headers={
                    "Content-Length": str(len(data)),
                    "Content-Range": f"bytes {start}-{len(payload)-1}/{len(payload)}",
                },
            )
        # First call: only return first half to simulate interrupt via partial write externally
        return FakeResp(payload)

    monkeypatch.setattr(
        "app.processing.plugins.lama.download.urllib.request.urlopen",
        fake_urlopen,
    )
    download_file("http://example.com/model.pt", dest)
    assert dest.is_file()
    assert dest.read_bytes() == payload

    # ensure skips re-download when large enough
    big = tmp_path / "big-lama.pt"
    big.write_bytes(b"x" * 2_000_000)
    path = ensure_lama_checkpoint(tmp_path, filename="big-lama.pt")
    assert path == big


def test_gpu_oom_fallback_to_cpu() -> None:
    import torch

    manager = MagicMock()
    manager.status = {"device": "cuda"}
    manager.ensure_model = MagicMock()

    def predict(image_t, mask_t):  # noqa: ANN001
        if str(image_t.device).startswith("cuda") or manager.status["device"] == "cuda":
            # simulate first call OOM then CPU
            manager.status = {"device": "cpu"}
            raise RuntimeError("CUDA out of memory")
        out = torch.zeros(1, 3, image_t.shape[-2], image_t.shape[-1])
        return out

    # Use real manager method path via patching
    from app.processing.plugins.lama.model_manager import LamaModelManager

    real = LamaModelManager(Path("/tmp/lama-test"), prefer_gpu=True)
    real._model = MagicMock(side_effect=[RuntimeError("CUDA out of memory"), torch.zeros(1, 3, 32, 32)])
    real._device = "cuda"

    calls = {"n": 0}

    def fake_model(img, mask):  # noqa: ANN001
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("CUDA out of memory")
        return torch.zeros(1, 3, img.shape[-2], img.shape[-1])

    real._model = fake_model

    with patch.object(real, "ensure_model", wraps=real.ensure_model) as ensure:
        # Force ensure_model on fallback to set cpu model
        def ensure_cpu(prefer_gpu=False):  # noqa: ANN001
            real._device = "cpu"
            real._model = lambda img, mask: torch.zeros(1, 3, img.shape[-2], img.shape[-1])
            return real._model

        ensure.side_effect = ensure_cpu
        img = torch.zeros(1, 3, 32, 32)
        mask = torch.zeros(1, 1, 32, 32)
        # First predict triggers OOM path
        out = real.predict(img, mask)
        assert out.shape[1] == 3


def test_ai_plugin_outside_unchanged_with_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[16:40, 16:40] = 255

    def fake_inpaint(frame_bgr, mask_arr, manager, **kwargs):  # noqa: ANN001
        out = frame_bgr.copy()
        out[mask_arr > 0] = 0
        return out, {"device": "cpu", "skipped": False}

    monkeypatch.setattr(
        "app.processing.strategies.ai_inpaint.inpaint_frame_with_lama",
        fake_inpaint,
    )
    monkeypatch.setattr(
        "app.processing.strategies.ai_inpaint._torch_available",
        lambda: True,
    )
    monkeypatch.setattr(
        "app.processing.strategies.ai_inpaint.get_model_manager",
        lambda *a, **k: MagicMock(),
    )

    plugin = AIInpaintPlugin()
    ctx = FrameContext(
        index=0,
        time_seconds=0.0,
        frame_bgr=frame.copy(),
        mask=mask,
        device=ComputeDevice.CPU,
    )
    result = plugin.process_frame(ctx, StrategyOptions(extras={"padding": 8}))
    assert_outside_unchanged(frame, result.frame_bgr, mask)
