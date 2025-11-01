"""Synthetic image benchmarking for keyframe selection, encoding, and OCR."""

from __future__ import annotations

import csv
import importlib.util
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np

# Ensure repository sources are importable when executed as a script.
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _ensure_perception_alias() -> None:
    """Load ``src.perception`` as a top-level ``perception`` module if required."""

    if "perception" in sys.modules:
        return

    perception_init = ROOT / "src" / "perception" / "__init__.py"
    if not perception_init.exists():
        return

    spec = importlib.util.spec_from_file_location("perception", perception_init)
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        sys.modules.setdefault("perception", module)
        spec.loader.exec_module(module)


_ensure_perception_alias()

from src.io.telemetry import MetricTimer, log_metric
from src.perception.ocr import MockOCR
from src.perception.vision_keyframe import VQEncoder, select_keyframes


ARTIFACTS_DIR = ROOT / "artifacts"
IMAGE_LATENCY_CSV = ARTIFACTS_DIR / "image_latency.csv"
OCR_RESULTS_CSV = ARTIFACTS_DIR / "ocr_results.csv"
PROVIDER = os.getenv("PROVIDER", "mock") or "mock"


@dataclass(frozen=True)
class ClipSpec:
    """Definition of a deterministic synthetic clip."""

    name: str
    frames: np.ndarray


def _make_static_clip(frames: int = 30) -> np.ndarray:
    """Generate a static clip with a central square panel."""

    base = np.full((frames, 64, 64, 3), 32, dtype=np.uint8)
    base[:, 16:48, 16:48, :] = 192
    return base


def _make_slow_move_clip(frames: int = 30) -> np.ndarray:
    """Generate a clip with a slowly moving bright square."""

    clip = np.zeros((frames, 64, 64, 3), dtype=np.uint8)
    for idx in range(frames):
        top = 8 + idx // 4
        left = 8 + idx // 4
        clip[idx, top : top + 24, left : left + 24, :] = 220
    return clip


def _make_fast_move_clip(frames: int = 30) -> np.ndarray:
    """Generate a clip with two rapidly moving panels."""

    clip = np.zeros((frames, 64, 64, 3), dtype=np.uint8)
    for idx in range(frames):
        offset = (idx * 5) % 32
        clip[idx, 4 + offset : 20 + offset, 6:30, :] = 255
        clip[idx, 32:52, (idx * 7) % 32 : ((idx * 7) % 32) + 16, :] = 160
    return clip


def _generate_clips() -> List[ClipSpec]:
    return [
        ClipSpec("static", _make_static_clip()),
        ClipSpec("slow_move", _make_slow_move_clip()),
        ClipSpec("fast_move", _make_fast_move_clip()),
    ]


def _run_clip_bench(clip: ClipSpec, encoder: VQEncoder) -> Dict[str, float | int | str]:
    """Run keyframe selection and encoding benchmarks for a clip."""

    frames_total = int(clip.frames.shape[0])

    with MetricTimer(
        "bench.image.select_keyframes",
        unit="ms",
        tags={"clip": clip.name, "provider": PROVIDER},
    ):
        keyframe_indices = select_keyframes(clip.frames, diff_tau=6.0, min_gap=2)

    keys_picked = int(len(keyframe_indices))
    keys_rate = keys_picked / max(frames_total, 1)

    log_metric(
        "vision.keys_rate",
        keys_rate,
        unit="ratio",
        tags={
            "clip": clip.name,
            "frames": str(frames_total),
            "provider": PROVIDER,
        },
    )

    keyframes = clip.frames[keyframe_indices]
    with MetricTimer(
        "bench.image.vq_encode",
        unit="ms",
        tags={
            "clip": clip.name,
            "provider": PROVIDER,
            "keyframes": str(keys_picked),
        },
    ):
        encoded = encoder.encode(keyframes)

    encode_ops = int(getattr(encoded, "shape", (keys_picked, 0))[0])
    log_metric(
        "vision.encode.ops",
        encode_ops,
        unit="count",
        tags={"clip": clip.name, "provider": PROVIDER},
    )

    return {
        "clip": clip.name,
        "frames_total": frames_total,
        "keys_picked": keys_picked,
        "keys_rate": keys_rate,
        "encode_ops": encode_ops,
        "provider": PROVIDER,
    }


def _write_latency_csv(rows: Sequence[Dict[str, float | int | str]]) -> None:
    IMAGE_LATENCY_CSV.parent.mkdir(parents=True, exist_ok=True)
    header = ["clip", "frames_total", "keys_picked", "keys_rate", "encode_ops", "provider"]
    with IMAGE_LATENCY_CSV.open("w", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(header)
        for row in rows:
            writer.writerow(
                [
                    row["clip"],
                    str(row["frames_total"]),
                    str(row["keys_picked"]),
                    f"{float(row['keys_rate']):.6f}",
                    str(row["encode_ops"]),
                    str(row["provider"]),
                ]
            )


def _create_synthetic_panels() -> Tuple[np.ndarray, List[Tuple[int, int, int, int]]]:
    canvas = np.zeros((96, 160, 3), dtype=np.uint8)
    panels = [
        (12, 10, 68, 54),
        (92, 28, 148, 70),
        (36, 58, 110, 90),
    ]
    for left, top, right, bottom in panels:
        canvas[top:bottom, left:right, :] = 240
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


def _evaluate_mock_ocr() -> Dict[str, float | int | str]:
    image_name = "synthetic_panels"
    image, expected = _create_synthetic_panels()
    start = time.perf_counter()
    result = MockOCR().text_and_boxes(image)
    latency_ms = (time.perf_counter() - start) * 1000.0

    predicted_boxes: Iterable[Tuple[int, int, int, int]] = result.get("boxes", ())  # type: ignore[assignment]
    predicted_words: Iterable[str] = result.get("text", "").split()

    predicted_list = list(predicted_boxes)
    words_list = list(predicted_words)
    matched: set[int] = set()
    for pred in predicted_list:
        for idx, truth in enumerate(expected):
            if idx in matched:
                continue
            if _iou(pred, truth) >= 0.5:
                matched.add(idx)
                break

    precision = len(matched) / max(len(predicted_list), 1)

    log_metric(
        "ocr.precision_synth",
        precision,
        unit="ratio",
        tags={
            "image": image_name,
            "panels": str(len(expected)),
            "provider": PROVIDER,
        },
    )
    log_metric(
        "ocr.latency_ms",
        latency_ms,
        unit="ms",
        tags={"scenario": image_name, "provider": PROVIDER},
    )
    log_metric(
        "ocr.words_detected",
        len(words_list),
        unit="count",
        tags={"image": image_name, "provider": PROVIDER},
    )
    log_metric(
        "ocr.boxes_detected",
        len(predicted_list),
        unit="count",
        tags={"image": image_name, "provider": PROVIDER},
    )

    return {
        "image": image_name,
        "words": len(words_list),
        "boxes": len(predicted_list),
        "precision_synthetic": precision,
        "provider": PROVIDER,
    }


def _write_ocr_csv(metrics: Dict[str, float | int | str]) -> None:
    OCR_RESULTS_CSV.parent.mkdir(parents=True, exist_ok=True)
    header = ["image", "words", "boxes", "precision_synthetic", "provider"]
    with OCR_RESULTS_CSV.open("w", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(header)
        writer.writerow(
            [
                metrics["image"],
                str(metrics["words"]),
                str(metrics["boxes"]),
                f"{float(metrics['precision_synthetic']):.6f}",
                str(metrics["provider"]),
            ]
        )


def main() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    encoder = VQEncoder(seed=0)
    rows: List[Dict[str, float | int | str]] = []
    for clip in _generate_clips():
        rows.append(_run_clip_bench(clip, encoder))
    _write_latency_csv(rows)

    ocr_metrics = _evaluate_mock_ocr()
    _write_ocr_csv(ocr_metrics)


if __name__ == "__main__":
    main()
