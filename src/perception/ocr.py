"""Offline-friendly optical character recognition helpers."""

from __future__ import annotations

import os
from collections import deque
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np

BBox = Tuple[int, int, int, int]


@dataclass
class MockOCR:
    """Synthetic OCR engine that identifies bright rectangular panels.

    The mock implementation searches for connected components within a binary
    threshold of the input image. Each detected component is converted into a
    bounding box and returned as a fabricated "PANEL" word. This keeps the
    interface compatible with real OCR backends while remaining completely
    offline.
    """

    intensity_threshold: int = 200
    min_area: int = 9

    def text_and_boxes(self, image: np.ndarray) -> Dict[str, Sequence]:
        """Return fabricated OCR results for bright rectangular regions.

        Parameters
        ----------
        image:
            A numpy array with shape ``(H, W)`` or ``(H, W, C)``. If the input is
            multichannel, it is converted to grayscale by averaging across the
            color axis.
        """

        if image.ndim == 3:
            grayscale = image.mean(axis=2)
        elif image.ndim == 2:
            grayscale = image.astype(np.float32)
        else:
            raise ValueError("Unsupported image shape for OCR mock.")

        mask = np.asarray(grayscale >= self.intensity_threshold, dtype=bool)
        components = list(self._connected_components(mask))

        words: List[str] = []
        boxes: List[BBox] = []
        conf: List[float] = []
        for idx, ((min_y, min_x), (max_y, max_x)) in enumerate(components):
            height = max_y - min_y + 1
            width = max_x - min_x + 1
            if height * width < self.min_area:
                continue
            words.append(f"PANEL{idx + 1}")
            boxes.append((int(min_x), int(min_y), int(max_x), int(max_y)))
            conf.append(0.95)

        full_text = " ".join(words)
        by_word = [
            {"text": word, "box": box, "conf": confidence}
            for word, box, confidence in zip(words, boxes, conf)
        ]

        return {
            "text": full_text,
            "boxes": tuple(boxes),
            "conf": tuple(conf),
            "by_word": tuple(by_word),
        }

    @staticmethod
    def _connected_components(mask: np.ndarray) -> Iterable[Tuple[Tuple[int, int], Tuple[int, int]]]:
        if mask.size == 0:
            return []

        visited = np.zeros_like(mask, dtype=bool)
        height, width = mask.shape
        for y in range(height):
            for x in range(width):
                if not mask[y, x] or visited[y, x]:
                    continue
                queue: deque[Tuple[int, int]] = deque([(y, x)])
                visited[y, x] = True
                min_y = max_y = y
                min_x = max_x = x
                while queue:
                    cy, cx = queue.popleft()
                    for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                        if 0 <= ny < height and 0 <= nx < width:
                            if mask[ny, nx] and not visited[ny, nx]:
                                visited[ny, nx] = True
                                queue.append((ny, nx))
                                if ny < min_y:
                                    min_y = ny
                                if ny > max_y:
                                    max_y = ny
                                if nx < min_x:
                                    min_x = nx
                                if nx > max_x:
                                    max_x = nx
                yield (min_y, min_x), (max_y, max_x)


def _env_flag(name: str) -> bool:
    value = os.getenv(name, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def text_and_boxes(image: np.ndarray) -> Dict[str, Sequence]:
    """Dispatch to the configured OCR engine."""

    if _env_flag("USE_EASYOCR"):
        raise RuntimeError("EasyOCR backend is not available in offline mode.")
    if _env_flag("USE_TESSERACT"):
        raise RuntimeError("Tesseract backend is not available in offline mode.")

    return MockOCR().text_and_boxes(image)


__all__ = ["MockOCR", "text_and_boxes"]
