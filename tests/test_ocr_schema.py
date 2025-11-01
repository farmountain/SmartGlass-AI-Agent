import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from src.perception.ocr import MockOCR, text_and_boxes


@pytest.mark.parametrize(
    "ocr_fn",
    [lambda image: MockOCR().text_and_boxes(image), text_and_boxes],
)
def test_mock_ocr_schema_on_blank_image(ocr_fn):
    image = np.zeros((16, 16), dtype=np.uint8)
    result = ocr_fn(image)

    assert set(result.keys()) == {"text", "boxes", "conf", "by_word"}
    assert isinstance(result["boxes"], tuple)
    assert isinstance(result["conf"], tuple)
    assert isinstance(result["by_word"], tuple)

    assert len(result["boxes"]) == len(result["conf"]) == len(result["by_word"])

    for box in result["boxes"]:
        assert isinstance(box, tuple)
        assert len(box) == 4
        assert all(isinstance(coord, int) for coord in box)

    for confidence in result["conf"]:
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0

    for word in result["by_word"]:
        assert set(word.keys()) == {"text", "box", "conf"}
        assert isinstance(word["text"], str)
        assert isinstance(word["box"], tuple)
        assert len(word["box"]) == 4
        assert isinstance(word["conf"], float)
        assert 0.0 <= word["conf"] <= 1.0
