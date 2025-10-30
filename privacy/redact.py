"""Deterministic redaction utilities for privacy-sensitive imagery."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Tuple, Union

import numpy as np

try:  # Pillow is an optional dependency for callers already using it.
    from PIL import Image
except ImportError:  # pragma: no cover - Pillow is available in runtime environments.
    Image = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

ArrayLike = Union[np.ndarray, "Image.Image"]


@dataclass(frozen=True)
class RedactionSummary:
    """Summary of deterministic redaction operations."""

    faces_masked: int
    plates_masked: int

    def as_dict(self) -> dict[str, int]:
        """Return a dictionary representation for structured logging."""

        return {"faces_masked": self.faces_masked, "plates_masked": self.plates_masked}


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


def _mask_block(redacted: np.ndarray, height: int, width: int, value: int, *, anchor: str) -> int:
    """Mask a block within the array at a deterministic anchor location."""

    if redacted.size == 0:
        return 0

    total_height, total_width = redacted.shape[:2]
    if total_height == 0 or total_width == 0:
        return 0

    h = min(height, total_height)
    w = min(width, total_width)
    if h == 0 or w == 0:
        return 0

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
    return 1


class DeterministicRedactor:
    """Simple deterministic redaction pipeline."""

    def __init__(self, face_mask_size: int = 12, plate_mask_size: int = 8) -> None:
        self.face_mask_size = face_mask_size
        self.plate_mask_size = plate_mask_size

    def __call__(self, image: ArrayLike) -> Tuple[ArrayLike, RedactionSummary]:
        """Apply deterministic redaction to the provided image."""

        array, restore = _ensure_array(image)
        faces = _mask_block(array, self.face_mask_size, self.face_mask_size, 0, anchor="top_left")
        plates = _mask_block(
            array,
            self.plate_mask_size,
            self.plate_mask_size * 2,
            255,
            anchor="bottom_right",
        )
        summary = RedactionSummary(faces_masked=faces, plates_masked=plates)
        logger.debug("Applied deterministic redaction", extra=summary.as_dict())
        return restore(array), summary


def redact_image(image: ArrayLike) -> Tuple[ArrayLike, RedactionSummary]:
    """Convenience function to redact an image using the default pipeline."""

    return DeterministicRedactor()(image)


__all__ = ["DeterministicRedactor", "RedactionSummary", "redact_image"]
