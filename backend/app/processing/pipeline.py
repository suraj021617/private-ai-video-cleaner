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
from app.processing.strategies import resolve_strategy
from app.processing.types import (
    ExportOptions,
    FrameContext,
    PipelineProgress,
    ProcessingStrategy,
    StrategyOptions,
)

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[PipelineProgress], None]
ControlCallback = Callable[[], str | None]  # returns "pause" | "cancel" | None


class VideoProcessingPipeline:
    """
    Decode → mask → strategy plugin → encode → mux audio.

    Guarantees:
    - Output fps/resolution match the source stream info used for reading
      (unless an explicit export size is requested, e.g. 4K)
    - Pixels outside the mask are never modified (plugin.composite / LaMa hard copy)
    - Original audio is stream-copied when present
    - GPU used when available; otherwise CPU
    - Unavailable AI strategies fall back automatically
    """

    def __init__(
        self,
        *,
        prefer_gpu: bool = True,
        strategy_options: StrategyOptions | None = None,
        export_format: str = "mp4",
        export_options: ExportOptions | None = None,
    ) -> None:
        self.prefer_gpu = prefer_gpu
        self.strategy_options = strategy_options or StrategyOptions()
        allowed = {"mp4", "mov", "mkv"}
        self.export_format = export_format if export_format in allowed else "mp4"
        self.export_options = export_options or ExportOptions(
            container=self.export_format
        )
        if self.export_options.container not in allowed:
            self.export_options.container = self.export_format
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
        on_control: ControlCallback | None = None,
    ) -> dict[str, Any]:
        plugin, strategy_used, fallback_from = resolve_strategy(strategy)
        if fallback_from is not None:
            logger.info(
                "Strategy %s unavailable; falling back to %s",
                fallback_from.value,
                strategy_used.value,
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
                export=self.export_options,
            )

            total = info.frame_count if info.frame_count > 0 else 0
            done = 0
            modified_frames = 0
            started = time.perf_counter()
            model_loaded = strategy_used in {
                ProcessingStrategy.AI_INPAINT,
                ProcessingStrategy.PROPAINTER,
                ProcessingStrategy.STTN,
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
                    strategy_used=strategy_used.value,
                    fallback_from=fallback_from.value if fallback_from else None,
                ),
            )

            for index, time_seconds, frame in reader:
                if on_control is not None:
                    signal = on_control()
                    if signal == "cancel":
                        raise AppError(
                            code="job_cancelled",
                            message="Job cancelled by user",
                            status_code=499,
                        )
                    while signal == "pause":
                        time.sleep(0.25)
                        signal = on_control()
                        if signal == "cancel":
                            raise AppError(
                                code="job_cancelled",
                                message="Job cancelled by user",
                                status_code=499,
                            )
                        if signal != "pause":
                            break

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
                try:
                    result = plugin.process_frame(ctx, self.strategy_options)
                except RuntimeError as exc:
                    # CUDA OOM → retry once on CPU via strategy extras
                    if "out of memory" in str(exc).lower():
                        logger.warning("OOM during processing; retrying frame on CPU")
                        extras = dict(self.strategy_options.extras)
                        extras["prefer_gpu"] = False
                        self.strategy_options.extras = extras
                        from app.processing.types import ComputeDevice

                        ctx.device = ComputeDevice.CPU
                        result = plugin.process_frame(ctx, self.strategy_options)
                    else:
                        raise
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
                            strategy_used=strategy_used.value,
                            fallback_from=(
                                fallback_from.value if fallback_from else None
                            ),
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
                    strategy_used=strategy_used.value,
                    fallback_from=fallback_from.value if fallback_from else None,
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
                    strategy_used=strategy_used.value,
                    fallback_from=fallback_from.value if fallback_from else None,
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
                "strategy": strategy_used.value,
                "strategy_requested": (
                    fallback_from.value if fallback_from else strategy_used.value
                ),
                "fallback_from": fallback_from.value if fallback_from else None,
                "export_format": self.export_format,
                "color_space": info.color_space,
                "hdr": info.hdr,
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
