"""Deterministic redaction utilities for privacy-sensitive imagery."""

from __future__ import annotations

import logging
from dataclasses import dataclass
import importlib
from typing import Callable, List, Optional, Tuple, Union

import numpy as np

try:  # Pillow is an optional dependency for callers already using it.
    from PIL import Image
except ImportError:  # pragma: no cover - Pillow is available in runtime environments.
    Image = None  # type: ignore[assignment]

_FACE_RECOGNITION_SPEC = importlib.util.find_spec("face_recognition")
face_recognition = importlib.import_module("face_recognition") if _FACE_RECOGNITION_SPEC else None  # type: ignore[assignment]

_MEDIAPIPE_SPEC = importlib.util.find_spec("mediapipe")
mediapipe = importlib.import_module("mediapipe") if _MEDIAPIPE_SPEC else None  # type: ignore[assignment]

_TESSERACT_SPEC = importlib.util.find_spec("pytesseract")
pytesseract = importlib.import_module("pytesseract") if _TESSERACT_SPEC else None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

ArrayLike = Union[np.ndarray, "Image.Image"]


@dataclass(frozen=True)
class RedactionSummary:
    """Summary of deterministic redaction operations."""

    faces_masked: int
    plates_masked: int
    total_masked_area: int

    def as_dict(self) -> dict[str, int]:
        """Return a dictionary representation for structured logging."""

        return {
            "faces_masked": self.faces_masked,
            "plates_masked": self.plates_masked,
            "total_masked_area": self.total_masked_area,
        }


def _ensure_array(image: ArrayLike) -> Tuple[np.ndarray, Callable[[np.ndarray], ArrayLike]]:
    """Convert the input image into a numpy array and provide a restorer."""

    if isinstance(image, np.ndarray):
        return image.copy(), lambda arr: arr
    if Image is not None and isinstance(image, Image.Image):
        array = np.array(image)

        def _restore(arr: np.ndarray) -> Image.Image:
            mode = image.mode or "RGB"
            return Image.fromarray(arr.astype(np.uint8), mode=mode)

        return array.copy(), _restore

    array = np.array(image)
    return array.copy(), lambda arr: arr


def _mask_block(
    redacted: np.ndarray, height: int, width: int, value: int, *, anchor: str
) -> Tuple[int, int]:
    """Mask a block within the array at a deterministic anchor location."""

    if redacted.size == 0:
        return 0, 0

    total_height, total_width = redacted.shape[:2]
    if total_height == 0 or total_width == 0:
        return 0, 0

    h = min(height, total_height)
    w = min(width, total_width)
    if h == 0 or w == 0:
        return 0, 0

    if anchor == "top_left":
        row_start, col_start = 0, 0
    elif anchor == "bottom_right":
        row_start = total_height - h
        col_start = total_width - w
    else:
        raise ValueError(f"Unknown anchor: {anchor}")

    row_end = row_start + h
    col_end = col_start + w
    redacted[row_start:row_end, col_start:col_end, ...] = value
    return 1, h * w


def _mask_rectangle(
    redacted: np.ndarray,
    box: Tuple[int, int, int, int],
    value: int,
    *,
    padding_ratio: float = 0.15,
) -> int:
    """Mask a rectangular region with optional padding and return its area."""

    if redacted.size == 0:
        return 0

    top, right, bottom, left = box
    height, width = redacted.shape[:2]

    pad_h = int((bottom - top) * padding_ratio)
    pad_w = int((right - left) * padding_ratio)

    top = max(0, top - pad_h)
    left = max(0, left - pad_w)
    bottom = min(height, bottom + pad_h)
    right = min(width, right + pad_w)

    if bottom <= top or right <= left:
        return 0

    redacted[top:bottom, left:right, ...] = value
    return (bottom - top) * (right - left)


def _detect_faces(image: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """Detect faces using available detection backends."""

    if face_recognition is not None:
        rgb_array = image[:, :, :3] if image.ndim == 3 else np.stack([image] * 3, axis=-1)
        return face_recognition.face_locations(rgb_array)  # type: ignore[call-arg]

    if mediapipe is not None:
        mp_image = image
        if image.ndim == 2:
            mp_image = np.stack([image] * 3, axis=-1)
        with mediapipe.solutions.face_detection.FaceDetection(  # type: ignore[attr-defined]
            model_selection=0, min_detection_confidence=0.5
        ) as detector:
            results = detector.process(mp_image)
            if not results.detections:
                return []

            detections = []
            img_h, img_w = mp_image.shape[:2]
            for detection in results.detections:
                rel_box = detection.location_data.relative_bounding_box
                xmin = int(rel_box.xmin * img_w)
                ymin = int(rel_box.ymin * img_h)
                w = int(rel_box.width * img_w)
                h = int(rel_box.height * img_h)
                detections.append((ymin, xmin + w, ymin + h, xmin))
            return detections

    return []


def _detect_plates(image: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """Detect license plates using OCR heuristics when available."""

    if pytesseract is None or Image is None:
        return []

    pil_image = Image.fromarray(image.astype(np.uint8))
    data = pytesseract.image_to_data(pil_image, output_type=pytesseract.Output.DICT)
    boxes: List[Tuple[int, int, int, int]] = []
    for left, top, width, height, conf in zip(
        data.get("left", []), data.get("top", []), data.get("width", []), data.get("height", []), data.get("conf", [])
    ):
        try:
            conf_val = float(conf)
        except (TypeError, ValueError):
            conf_val = 0.0

        if conf_val < 60 or width == 0 or height == 0:
            continue

        aspect_ratio = width / float(height)
        if aspect_ratio >= 2.5 and width > 20 and height > 10:
            boxes.append((top, left + width, top + height, left))
    return boxes


class DeterministicRedactor:
    """Simple deterministic redaction pipeline."""

    def __init__(
        self,
        face_mask_size: int = 12,
        plate_mask_size: int = 8,
        mask_width: Optional[float] = None,
        mask_height: Optional[float] = None,
        face_padding_ratio: float = 0.15,
        plate_padding_ratio: float = 0.1,
        enable_face_detection: bool = True,
        enable_plate_detection: bool = True,
    ) -> None:
        self.face_mask_size = face_mask_size
        self.plate_mask_size = plate_mask_size
        self.mask_width = mask_width
        self.mask_height = mask_height
        self.face_padding_ratio = face_padding_ratio
        self.plate_padding_ratio = plate_padding_ratio
        self.enable_face_detection = enable_face_detection
        self.enable_plate_detection = enable_plate_detection

    @staticmethod
    def _resolve_dimension(spec: Optional[float], *, default: int, max_dim: int) -> int:
        """Resolve an absolute or fractional dimension into pixels."""

        if spec is None:
            return default

        if isinstance(spec, float) and 0 < spec <= 1:
            return max(1, int(max_dim * spec))

        resolved = int(spec)
        return max(1, resolved)

    def __call__(self, image: ArrayLike) -> Tuple[ArrayLike, RedactionSummary]:
        """Apply deterministic redaction to the provided image."""

        array, restore = _ensure_array(image)

        height, width = array.shape[:2] if array.size else (0, 0)

        faces_masked = 0
        plates_masked = 0
        total_area = 0

        face_boxes = _detect_faces(array) if self.enable_face_detection else []
        if face_boxes:
            for box in face_boxes:
                masked_area = _mask_rectangle(
                    array, box, 0, padding_ratio=self.face_padding_ratio
                )
                if masked_area > 0:
                    faces_masked += 1
                    total_area += masked_area
        else:
            face_width = self._resolve_dimension(
                self.mask_width, default=self.face_mask_size, max_dim=width
            )
            face_height = self._resolve_dimension(
                self.mask_height, default=self.face_mask_size, max_dim=height
            )
            faces, area = _mask_block(array, face_height, face_width, 0, anchor="top_left")
            faces_masked += faces
            total_area += area

        plate_boxes = _detect_plates(array) if self.enable_plate_detection else []
        if plate_boxes:
            for box in plate_boxes:
                masked_area = _mask_rectangle(
                    array, box, 0, padding_ratio=self.plate_padding_ratio
                )
                if masked_area > 0:
                    plates_masked += 1
                    total_area += masked_area
        else:
            plate_height = self._resolve_dimension(
                self.mask_height, default=self.plate_mask_size, max_dim=height
            )
            plate_width = self._resolve_dimension(
                self.mask_width,
                default=self.plate_mask_size * 2,
                max_dim=width,
            )
            plates, area = _mask_block(
                array,
                plate_height,
                plate_width,
                255,
                anchor="bottom_right",
            )
            plates_masked += plates
            total_area += area

        summary = RedactionSummary(
            faces_masked=faces_masked, plates_masked=plates_masked, total_masked_area=total_area
        )
        logger.debug("Applied deterministic redaction", extra=summary.as_dict())
        return restore(array), summary


def redact_image(image: ArrayLike) -> Tuple[ArrayLike, RedactionSummary]:
    """Convenience function to redact an image using the default pipeline."""

    return DeterministicRedactor()(image)


__all__ = ["DeterministicRedactor", "RedactionSummary", "redact_image"]
