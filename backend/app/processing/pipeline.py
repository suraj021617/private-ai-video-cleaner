"""Modular video processing pipeline."""

from __future__ import annotations

import logging
import shutil
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.core.errors import AppError
from app.processing.device import detect_compute_device
from app.processing.ffmpeg_io import FrameReader, FrameWriter
from app.processing.mask_raster import rasterize_mask
from app.processing.strategies import get_plugin
from app.processing.types import (
    FrameContext,
    PipelineProgress,
    ProcessingStrategy,
    StrategyOptions,
)

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[PipelineProgress], None]


class VideoProcessingPipeline:
    """
    Decode → mask → strategy plugin → encode → mux audio.

    Guarantees:
    - Output fps/resolution match the source stream info used for reading
    - Pixels outside the mask are never modified (plugin.composite / LaMa hard copy)
    - Original audio is stream-copied when present
    - GPU used when available; otherwise CPU
    """

    def __init__(
        self,
        *,
        prefer_gpu: bool = True,
        strategy_options: StrategyOptions | None = None,
        export_format: str = "mp4",
    ) -> None:
        self.prefer_gpu = prefer_gpu
        self.strategy_options = strategy_options or StrategyOptions()
        self.export_format = export_format if export_format in {"mp4", "mov"} else "mp4"
        self.device = detect_compute_device(prefer_gpu=prefer_gpu)

    def run(
        self,
        *,
        source_path: Path,
        output_path: Path,
        work_dir: Path,
        strategy: ProcessingStrategy | str,
        mask_payload: dict[str, Any],
        on_progress: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        plugin = get_plugin(strategy)
        if not plugin.available:
            raise AppError(
                code="strategy_unavailable",
                message=f"Strategy '{plugin.name.value}' is not available",
                status_code=501,
            )

        work_dir.mkdir(parents=True, exist_ok=True)
        reader: FrameReader | None = None
        writer: FrameWriter | None = None

        try:
            reader = FrameReader(source_path)
            info = reader.info
            if info.width <= 0 or info.height <= 0 or info.fps <= 0:
                raise AppError(
                    code="invalid_source_stream",
                    message="Source video has invalid fps or resolution",
                    status_code=422,
                )

            writer = FrameWriter(
                output_path=output_path,
                source_path=source_path,
                info=info,
                temp_dir=work_dir / "encode",
                container=self.export_format,
            )

            total = info.frame_count if info.frame_count > 0 else 0
            done = 0
            modified_frames = 0
            started = time.perf_counter()
            model_loaded = strategy in {
                ProcessingStrategy.AI_INPAINT,
                ProcessingStrategy.AI_INPAINT.value,
            }
            self._emit(
                on_progress,
                PipelineProgress(
                    status="running",
                    frames_total=total,
                    frames_done=0,
                    percent=0.0,
                    message="Decoding and processing frames",
                    device=self.device.value,
                    fps=0.0,
                    eta_seconds=None,
                    model_loaded=model_loaded if model_loaded else None,
                ),
            )

            for index, time_seconds, frame in reader:
                mask = rasterize_mask(
                    payload=mask_payload,
                    frame_width=info.width,
                    frame_height=info.height,
                    time_seconds=time_seconds,
                )
                ctx = FrameContext(
                    index=index,
                    time_seconds=time_seconds,
                    frame_bgr=frame,
                    mask=mask,
                    device=self.device,
                )
                result = plugin.process_frame(ctx, self.strategy_options)
                if result.pixels_modified > 0:
                    modified_frames += 1
                writer.write(result.frame_bgr)
                done += 1
                elapsed = max(time.perf_counter() - started, 1e-6)
                proc_fps = done / elapsed
                remaining = (total - done) / proc_fps if total > done and proc_fps > 0 else 0.0
                if total > 0 and (done % 2 == 0 or done == total):
                    percent = min(99.0, round((done / total) * 100, 2))
                    self._emit(
                        on_progress,
                        PipelineProgress(
                            status="running",
                            frames_total=total,
                            frames_done=done,
                            percent=percent,
                            message=f"Processed frame {done}/{total}",
                            device=result.device.value,
                            fps=round(proc_fps, 2),
                            eta_seconds=round(remaining, 1),
                            model_loaded=True if model_loaded else None,
                        ),
                    )

            if total == 0:
                total = done

            self._emit(
                on_progress,
                PipelineProgress(
                    status="encoding",
                    frames_total=total,
                    frames_done=done,
                    percent=99.0,
                    message="Muxing video and original audio",
                    device=self.device.value,
                    fps=round(done / max(time.perf_counter() - started, 1e-6), 2),
                    eta_seconds=0.0,
                    model_loaded=True if model_loaded else None,
                ),
            )
            final_path = writer.finalize()

            self._emit(
                on_progress,
                PipelineProgress(
                    status="completed",
                    frames_total=total,
                    frames_done=done,
                    percent=100.0,
                    message="Processing complete",
                    device=self.device.value,
                    fps=round(done / max(time.perf_counter() - started, 1e-6), 2),
                    eta_seconds=0.0,
                    model_loaded=True if model_loaded else None,
                ),
            )

            return {
                "output_path": str(final_path),
                "frames_processed": done,
                "frames_modified": modified_frames,
                "fps": info.fps,
                "width": info.width,
                "height": info.height,
                "has_audio": info.has_audio,
                "device": self.device.value,
                "strategy": plugin.name.value,
                "export_format": self.export_format,
            }
        finally:
            if reader is not None:
                reader.release()
            if writer is not None:
                writer.close()

    @staticmethod
    def _emit(
        callback: ProgressCallback | None, progress: PipelineProgress
    ) -> None:
        if callback is None:
            return
        try:
            callback(progress)
        except Exception:  # noqa: BLE001
            logger.exception("Progress callback failed")


def cleanup_work_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
