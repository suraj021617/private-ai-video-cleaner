"""Lightweight stress / regression smoke checks for production readiness."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from app.processing.device import benchmark_devices, memory_status
from app.processing.mask_raster import assert_outside_unchanged, rasterize_mask
from app.processing.pipeline import VideoProcessingPipeline
from app.processing.types import ProcessingStrategy


def test_device_benchmark_and_memory_snapshot() -> None:
    bench = benchmark_devices()
    assert "cpu_ms" in bench
    assert "recommended" in bench
    mem = memory_status()
    assert "rss_mb" in mem


def test_large_frame_mask_raster_does_not_touch_outside() -> None:
    # Synthetic 1080p-ish frame path without needing a huge fixture file
    w, h = 1920, 1080
    payload = {
        "version": 1,
        "items": [
            {
                "id": "r1",
                "type": "rect",
                "x": 0.4,
                "y": 0.4,
                "w": 0.1,
                "h": 0.1,
                "start_time": 0,
                "end_time": 1,
            }
        ],
        "expansion": 4,
        "feather": 8,
        "edge_refine": 2,
    }
    mask = rasterize_mask(
        payload=payload, frame_width=w, frame_height=h, time_seconds=0.0
    )
    assert mask.shape == (h, w)
    assert mask[0, 0] == 0
    assert np.count_nonzero(mask) > 0


def test_pipeline_mkv_fast_export(tmp_path: Path, sample_video: Path) -> None:
    from app.processing.types import ExportOptions

    payload = {
        "version": 1,
        "items": [
            {
                "id": "r1",
                "type": "rect",
                "x": 0.1,
                "y": 0.1,
                "w": 0.2,
                "h": 0.2,
                "start_time": 0,
                "end_time": 10,
            }
        ],
    }
    output = tmp_path / "out.mkv"
    result = VideoProcessingPipeline(
        prefer_gpu=False,
        export_format="mkv",
        export_options=ExportOptions(
            container="mkv", codec="h264", quality="fast"
        ),
    ).run(
        source_path=sample_video,
        output_path=output,
        work_dir=tmp_path / "work",
        strategy=ProcessingStrategy.BLUR,
        mask_payload=payload,
    )
    assert output.is_file()
    assert result["export_format"] == "mkv"
    assert result["strategy"] == "blur"
