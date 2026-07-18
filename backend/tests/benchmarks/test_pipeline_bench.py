"""Benchmark tests for the processing pipeline."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from app.processing.pipeline import VideoProcessingPipeline
from app.processing.types import ProcessingStrategy


@pytest.fixture()
def bench_video(tmp_path: Path) -> Path:
    """Generate a short deterministic clip for benchmarks."""
    import subprocess

    path = tmp_path / "bench.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=640x360:rate=30:duration=2",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=880:duration=2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(path),
        ],
        check=True,
        capture_output=True,
    )
    return path


MASK = {
    "version": 1,
    "items": [
        {
            "id": "r1",
            "type": "rect",
            "x": 0.25,
            "y": 0.25,
            "w": 0.3,
            "h": 0.3,
            "start_time": 0,
            "end_time": 10,
        }
    ],
}


@pytest.mark.benchmark
@pytest.mark.parametrize(
    "strategy",
    [
        ProcessingStrategy.BLUR,
        ProcessingStrategy.FILL,
        ProcessingStrategy.CLASSIC_INPAINT,
    ],
)
def test_benchmark_pipeline_strategies(
    strategy: ProcessingStrategy, bench_video: Path, tmp_path: Path
) -> None:
    output = tmp_path / f"{strategy.value}.mp4"
    work = tmp_path / f"work_{strategy.value}"
    pipeline = VideoProcessingPipeline(prefer_gpu=True)

    started = time.perf_counter()
    result = pipeline.run(
        source_path=bench_video,
        output_path=output,
        work_dir=work,
        strategy=strategy,
        mask_payload=MASK,
    )
    elapsed = time.perf_counter() - started

    assert output.is_file()
    assert result["frames_processed"] > 0
    fps_effective = result["frames_processed"] / elapsed if elapsed > 0 else 0
    # Soft floor: environment-dependent, but should process a 2s 360p clip reasonably.
    assert elapsed < 120, f"{strategy.value} took too long: {elapsed:.2f}s"
    print(
        f"[benchmark] strategy={strategy.value} device={result['device']} "
        f"frames={result['frames_processed']} elapsed={elapsed:.3f}s "
        f"fps={fps_effective:.2f}"
    )


@pytest.mark.benchmark
def test_benchmark_cpu_vs_gpu_flag(bench_video: Path, tmp_path: Path) -> None:
    """Compare prefer_gpu True/False. On hosts without GPU both use CPU."""
    timings: dict[str, float] = {}
    for prefer_gpu in (False, True):
        output = tmp_path / f"gpu_{prefer_gpu}.mp4"
        work = tmp_path / f"work_gpu_{prefer_gpu}"
        started = time.perf_counter()
        result = VideoProcessingPipeline(prefer_gpu=prefer_gpu).run(
            source_path=bench_video,
            output_path=output,
            work_dir=work,
            strategy=ProcessingStrategy.BLUR,
            mask_payload=MASK,
        )
        timings[f"prefer_gpu={prefer_gpu}"] = time.perf_counter() - started
        print(
            f"[benchmark] prefer_gpu={prefer_gpu} device={result['device']} "
            f"elapsed={timings[f'prefer_gpu={prefer_gpu}']:.3f}s"
        )
    assert all(v < 120 for v in timings.values())
