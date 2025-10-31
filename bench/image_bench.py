"""Synthetic image benchmarking for keyframe selection, encoding, and OCR."""

from __future__ import annotations

import csv
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

# Ensure repository sources are importable when executed as a script.
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.io.telemetry import MetricTimer, log_metric
from src.perception.ocr import MockOCR
from src.perception.vision_keyframe import VQEncoder, select_keyframes


ARTIFACTS_DIR = ROOT / "artifacts"
IMAGE_LATENCY_CSV = ARTIFACTS_DIR / "image_latency.csv"
OCR_RESULTS_CSV = ARTIFACTS_DIR / "ocr_results.csv"


@dataclass(frozen=True)
class ClipSpec:
    """Definition of a deterministic synthetic clip."""

    name: str
    frames: np.ndarray


def _make_static_clip(frames: int = 30) -> np.ndarray:
    base = np.full((frames, 64, 64, 3), 42, dtype=np.uint8)
    overlay = np.zeros_like(base)
    overlay[:, 16:48, 16:48, :] = 85
    return (base + overlay).astype(np.uint8)


def _make_gradient_clip(frames: int = 30) -> np.ndarray:
    grid_x = np.linspace(0, 1, 64, dtype=np.float32)
    grid_y = np.linspace(0, 1, 64, dtype=np.float32)
    xv, yv = np.meshgrid(grid_x, grid_y, indexing="xy")
    base = (xv + yv)[None, ..., None]
    time_offsets = np.linspace(0.0, 1.0, frames, dtype=np.float32)[:, None, None, None]
    clip = (base + time_offsets) * 127.0
    clip = np.clip(clip, 0, 255).astype(np.uint8)
    return np.repeat(clip, 3, axis=3)


def _make_motion_clip(frames: int = 30) -> np.ndarray:
    clip = np.zeros((frames, 64, 64, 3), dtype=np.uint8)
    for idx in range(frames):
        top = 8 + (idx * 2) % 32
        left = 4 + (idx * 3) % 32
        clip[idx, top : top + 16, left : left + 16, :] = 255
        clip[idx, top + 20 : top + 28, left + 24 : left + 40, :] = 170
    return clip


def _generate_clips() -> List[ClipSpec]:
    return [
        ClipSpec("static", _make_static_clip()),
        ClipSpec("gradient", _make_gradient_clip()),
        ClipSpec("motion", _make_motion_clip()),
    ]


def _run_clip_bench(clip: ClipSpec, encoder: VQEncoder) -> List[Tuple[str, float, int]]:
    """Run keyframe selection and encoding benchmarks for a clip."""

    num_frames = int(clip.frames.shape[0])
    results: List[Tuple[str, float, int]] = []

    with MetricTimer(
        "bench.image.select_keyframes", unit="ms", tags={"clip": clip.name}
    ) as timer:
        keyframe_indices = select_keyframes(clip.frames, diff_tau=6.0, min_gap=2)
    elapsed_select = timer.elapsed or 0.0
    results.append(("select_keyframes", elapsed_select, len(keyframe_indices)))

    keyframe_rate = max(len(keyframe_indices) - 1, 0) / max(num_frames - 1, 1)
    log_metric(
        "vision.keys_rate",
        keyframe_rate,
        unit="ratio",
        tags={"clip": clip.name, "frames": str(num_frames)},
    )

    keyframes = clip.frames[keyframe_indices]

    with MetricTimer(
        "bench.image.vq_encode", unit="ms", tags={"clip": clip.name}
    ) as timer:
        _ = encoder.encode(keyframes)
    elapsed_encode = timer.elapsed or 0.0
    results.append(("vq_encode", elapsed_encode, len(keyframe_indices)))

    return results


def _write_latency_csv(rows: List[Tuple[str, str, float, int]]) -> None:
    IMAGE_LATENCY_CSV.parent.mkdir(parents=True, exist_ok=True)
    with IMAGE_LATENCY_CSV.open("w", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(["clip", "stage", "ms", "keyframes"])
        for clip_name, stage, elapsed, keyframes in rows:
            writer.writerow([clip_name, stage, f"{elapsed:.6f}", str(keyframes)])


def _create_synthetic_panels() -> Tuple[np.ndarray, List[Tuple[int, int, int, int]]]:
    canvas = np.zeros((72, 128, 3), dtype=np.uint8)
    panels = [
        (12, 10, 52, 38),
        (70, 24, 114, 60),
    ]
    for left, top, right, bottom in panels:
        canvas[top: bottom, left: right, :] = 240
    expected = [(left, top, right - 1, bottom - 1) for left, top, right, bottom in panels]
    return canvas, expected


def _iou(box_a: Tuple[int, int, int, int], box_b: Tuple[int, int, int, int]) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    if inter_x2 < inter_x1 or inter_y2 < inter_y1:
        return 0.0
    inter_area = (inter_x2 - inter_x1 + 1) * (inter_y2 - inter_y1 + 1)
    area_a = (ax2 - ax1 + 1) * (ay2 - ay1 + 1)
    area_b = (bx2 - bx1 + 1) * (by2 - by1 + 1)
    union = area_a + area_b - inter_area
    return inter_area / union if union else 0.0


def _evaluate_mock_ocr() -> Dict[str, float]:
    image, expected = _create_synthetic_panels()
    start = time.perf_counter()
    result = MockOCR().text_and_boxes(image)
    elapsed = (time.perf_counter() - start) * 1000.0

    predicted = list(result.get("boxes", ()))
    matched: set[int] = set()
    for pred in predicted:
        for idx, truth in enumerate(expected):
            if idx in matched:
                continue
            if _iou(pred, truth) >= 0.5:
                matched.add(idx)
                break

    precision = len(matched) / max(len(predicted), 1)

    log_metric(
        "ocr.precision_synth",
        precision,
        unit="ratio",
        tags={"panels": str(len(expected))},
    )
    log_metric("ocr.latency_ms", elapsed, unit="ms", tags={"scenario": "synthetic_panels"})

    return {
        "expected_panels": float(len(expected)),
        "detected_panels": float(len(predicted)),
        "matched_panels": float(len(matched)),
        "precision": precision,
        "latency_ms": elapsed,
    }


def _write_ocr_csv(metrics: Dict[str, float]) -> None:
    OCR_RESULTS_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OCR_RESULTS_CSV.open("w", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(["metric", "value"])
        for key, value in metrics.items():
            writer.writerow([key, f"{value:.6f}"])


def main() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    encoder = VQEncoder(seed=0)
    rows: List[Tuple[str, str, float, int]] = []
    for clip in _generate_clips():
        for stage, elapsed, keyframes in _run_clip_bench(clip, encoder):
            rows.append((clip.name, stage, elapsed, keyframes))
    _write_latency_csv(rows)

    ocr_metrics = _evaluate_mock_ocr()
    _write_ocr_csv(ocr_metrics)


if __name__ == "__main__":
    main()
