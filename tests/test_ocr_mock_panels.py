import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.perception.ocr import MockOCR


def test_mock_ocr_detects_panels():
    image = np.zeros((128, 128, 3), dtype=np.uint8)
    image[16:48, 16:48] = 255
    image[80:112, 80:112] = 255

    result = MockOCR().text_and_boxes(image)

    assert len(result["by_word"]) >= 2
    assert "PANEL" in result["text"]
