"""Offline-friendly optical character recognition helpers."""

from __future__ import annotations

import os
from collections import deque
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from importlib.util import find_spec

import numpy as np

BBox = Tuple[int, int, int, int]

_EASYOCR_READER = None
_TESSERACT_CLIENT = None


def _prepare_image(image: np.ndarray) -> np.ndarray:
    array = np.asarray(image)
    if array.ndim not in (2, 3):
        raise ValueError("Unsupported image shape for OCR processing.")
    if array.ndim == 3 and array.shape[2] == 4:
        array = array[:, :, :3]
    return array


def _assemble_result(words: Sequence[str], boxes: Sequence[Sequence[int]], conf: Sequence[float]) -> Dict[str, Sequence]:
    normalized_boxes = tuple(tuple(int(coord) for coord in box) for box in boxes)
    normalized_conf = tuple(float(min(max(score, 0.0), 1.0)) for score in conf)
    normalized_words = [str(word) for word in words]
    by_word = tuple(
        {
            "text": word,
            "box": normalized_boxes[idx],
            "conf": normalized_conf[idx],
        }
        for idx, word in enumerate(normalized_words)
    )

    text = " ".join(word for word in normalized_words if word)

    return {
        "text": text,
        "boxes": normalized_boxes,
        "conf": normalized_conf,
        "by_word": by_word,
    }


@dataclass
class MockOCR:
    """Synthetic OCR engine that identifies bright rectangular panels."""

    intensity_threshold: int = 200
    min_area: int = 9

    def text_and_boxes(self, image: np.ndarray) -> Dict[str, Sequence]:
        """Return fabricated OCR results for bright rectangular regions."""

        array = _prepare_image(image)
        if array.ndim == 3:
            grayscale = array.mean(axis=2)
        else:
            grayscale = array.astype(np.float32)

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

        return _assemble_result(words, boxes, conf)

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


def _is_easyocr_available() -> bool:
    try:
        return find_spec("easyocr") is not None
    except Exception:  # pragma: no cover - defensive check
        return False


def _is_tesseract_available() -> bool:
    try:
        return find_spec("pytesseract") is not None
    except Exception:  # pragma: no cover - defensive check
        return False


def get_ocr_backend(preferred: Optional[str] = None) -> Callable[[np.ndarray], Dict[str, Sequence]]:
    """Select an OCR backend based on availability and preference."""

    normalized = preferred.lower() if preferred else None
    if normalized not in {None, "easyocr", "tesseract"}:
        raise ValueError(
            "Unsupported OCR backend preference. Choose 'easyocr' or 'tesseract'."
        )

    availability = {
        "easyocr": _is_easyocr_available(),
        "tesseract": _is_tesseract_available(),
    }

    candidates: Tuple[str, ...]
    if normalized:
        candidates = (normalized,) + tuple(
            backend for backend in ("easyocr", "tesseract") if backend != normalized
        )
    else:
        candidates = ("easyocr", "tesseract")

    for backend in candidates:
        if availability.get(backend):
            return _easyocr_text_and_boxes if backend == "easyocr" else _tesseract_text_and_boxes

    raise RuntimeError(
        "No OCR backends are available. Install EasyOCR (`pip install easyocr`) or "
        "pytesseract with the Tesseract binary (`pip install pytesseract` and "
        "`sudo apt-get install tesseract-ocr`)."
    )


def _easyocr_text_and_boxes(image: np.ndarray) -> Dict[str, Sequence]:
    global _EASYOCR_READER
    try:
        import easyocr  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "EasyOCR backend requested but the 'easyocr' package is not installed. "
            "Install it with `pip install easyocr`."
        ) from exc

    if _EASYOCR_READER is None:  # pragma: no cover - optional dependency
        _EASYOCR_READER = easyocr.Reader(["en"], gpu=False)

    return _assemble_result(*_easyocr_parse(_EASYOCR_READER, image))


def _tesseract_text_and_boxes(image: np.ndarray) -> Dict[str, Sequence]:
    global _TESSERACT_CLIENT
    try:
        import pytesseract  # type: ignore
        from pytesseract import Output  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "Tesseract backend requested but the 'pytesseract' package is not installed. "
            "Install it with `pip install pytesseract` and ensure the Tesseract binary "
            "is available (e.g., `sudo apt-get install tesseract-ocr`)."
        ) from exc

    if _TESSERACT_CLIENT is None:
        _TESSERACT_CLIENT = (pytesseract, Output)

    return _assemble_result(*_tesseract_parse(*_TESSERACT_CLIENT, image))


def text_and_boxes(image: np.ndarray) -> Dict[str, Sequence]:
    """Dispatch to the configured OCR engine."""

    array = _prepare_image(image)

    use_easyocr = _env_flag("USE_EASYOCR")
    use_tesseract = _env_flag("USE_TESSERACT")
    if use_easyocr and use_tesseract:
        raise RuntimeError("Only one OCR backend may be enabled at a time.")

    preferred = "easyocr" if use_easyocr else "tesseract" if use_tesseract else None
    backend = get_ocr_backend(preferred)

    return backend(array)


class EasyOCR:
    """Wrapper around the EasyOCR library for extracting text and boxes."""

    def __init__(self, languages: Optional[Sequence[str]] = None, gpu: bool = False):
        try:
            import easyocr  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "EasyOCR backend requested but the 'easyocr' package is not installed. "
                "Install it with `pip install easyocr`."
            ) from exc

        self._reader = easyocr.Reader(list(languages or ["en"]), gpu=gpu)

    def __call__(self, image: np.ndarray) -> Tuple[str, Tuple[Tuple[str, BBox], ...]]:
        words, boxes, conf = _easyocr_parse(self._reader, image)
        assembled = _assemble_result(words, boxes, conf)
        per_word = tuple((entry["text"], entry["box"]) for entry in assembled["by_word"])
        return assembled["text"], per_word


class TesseractOCR:
    """Wrapper around pytesseract for extracting text and boxes."""

    def __init__(self):
        try:
            import pytesseract  # type: ignore
            from pytesseract import Output  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "Tesseract backend requested but the 'pytesseract' package is not installed. "
                "Install it with `pip install pytesseract` and ensure the Tesseract binary "
                "is available (e.g., `sudo apt-get install tesseract-ocr`)."
            ) from exc

        self._pytesseract = pytesseract
        self._output = Output

    def __call__(self, image: np.ndarray) -> Tuple[str, Tuple[Tuple[str, BBox], ...]]:
        words, boxes, conf = _tesseract_parse(self._pytesseract, self._output, image)
        assembled = _assemble_result(words, boxes, conf)
        per_word = tuple((entry["text"], entry["box"]) for entry in assembled["by_word"])
        return assembled["text"], per_word


def _easyocr_parse(reader, image: np.ndarray) -> Tuple[Sequence[str], Sequence[BBox], Sequence[float]]:
    array = _prepare_image(image)
    results = reader.readtext(array, detail=1)

    words: List[str] = []
    boxes: List[BBox] = []
    conf: List[float] = []
    for bbox, text, confidence in results:
        if not text:
            continue
        xs = [point[0] for point in bbox]
        ys = [point[1] for point in bbox]
        boxes.append((int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))))
        words.append(text)
        conf.append(float(confidence))

    return words, boxes, conf


def _tesseract_parse(
    pytesseract, Output, image: np.ndarray
) -> Tuple[Sequence[str], Sequence[BBox], Sequence[float]]:
    array = _prepare_image(image)
    if array.ndim == 3:
        grayscale = array.mean(axis=2).astype(np.uint8)
    else:
        grayscale = array.astype(np.uint8)

    data = pytesseract.image_to_data(grayscale, output_type=Output.DICT)

    words: List[str] = []
    boxes: List[BBox] = []
    conf: List[float] = []
    for text, conf_value, left, top, width, height in zip(
        data.get("text", []),
        data.get("conf", []),
        data.get("left", []),
        data.get("top", []),
        data.get("width", []),
        data.get("height", []),
    ):
        stripped = text.strip()
        if not stripped:
            continue
        confidence = float(conf_value) if conf_value not in {"", None} else -1.0
        if confidence < 0:
            continue
        score = confidence / 100.0
        boxes.append((int(left), int(top), int(left + width), int(top + height)))
        words.append(stripped)
        conf.append(score)

    return words, boxes, conf


__all__ = [
    "EasyOCR",
    "MockOCR",
    "TesseractOCR",
    "get_ocr_backend",
    "text_and_boxes",
]
