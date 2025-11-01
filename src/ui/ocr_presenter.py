"""Helpers for presenting OCR results on different surfaces."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Sequence, Tuple

BBox = Tuple[int, int, int, int]


def _as_box(box: Iterable[int]) -> BBox:
    values = tuple(int(coord) for coord in box)
    if len(values) != 4:
        raise ValueError("OCR bounding boxes must contain four coordinates.")
    return values  # type: ignore[return-value]


def _normalize_by_word(entries: Sequence[Dict[str, Any]]) -> Tuple[Dict[str, Any], ...]:
    normalized = []
    for entry in entries:
        text = str(entry.get("text", ""))
        box = _as_box(entry.get("box", (0, 0, 0, 0))) if entry.get("box") is not None else (0, 0, 0, 0)
        conf = float(entry.get("conf", 0.0))
        normalized.append({"text": text, "box": box, "conf": conf})
    return tuple(normalized)


def _normalize_payload(ocr_result: Dict[str, Any]) -> Dict[str, Any]:
    boxes = tuple(_as_box(box) for box in ocr_result.get("boxes", ()))
    conf = tuple(float(score) for score in ocr_result.get("conf", ()))
    by_word_entries = _normalize_by_word(ocr_result.get("by_word", ()))

    return {
        "text": str(ocr_result.get("text", "")),
        "boxes": boxes,
        "conf": conf,
        "by_word": by_word_entries,
    }


def present_ocr(provider: Any, ocr_result: Dict[str, Any]) -> Dict[str, Any]:
    """Render OCR output on overlays or return a phone card payload."""

    payload = _normalize_payload(ocr_result)
    has_display = getattr(provider, "has_display", None)
    if callable(has_display) and has_display():
        provider.display.render(payload)
    return payload


__all__ = ["present_ocr"]
