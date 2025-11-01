import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ui.ocr_presenter import present_ocr


class _Display:
    def __init__(self):
        self.rendered = None

    def render(self, payload):
        self.rendered = payload


class _ProviderWithDisplay:
    def __init__(self):
        self.display = _Display()

    def has_display(self):
        return True


class _ProviderWithoutDisplay:
    def has_display(self):
        return False


def test_present_ocr_overlay_and_phone_match():
    ocr_result = {
        "text": "PANEL1 PANEL2",
        "boxes": ((0, 0, 10, 10), (20, 20, 40, 40)),
        "conf": (0.95, 0.85),
        "by_word": (
            {"text": "PANEL1", "box": (0, 0, 10, 10), "conf": 0.95},
            {"text": "PANEL2", "box": (20, 20, 40, 40), "conf": 0.85},
        ),
    }

    overlay_provider = _ProviderWithDisplay()
    phone_provider = _ProviderWithoutDisplay()

    overlay_payload = present_ocr(overlay_provider, ocr_result)
    phone_payload = present_ocr(phone_provider, ocr_result)

    assert overlay_provider.display.rendered == phone_payload
    assert overlay_payload == phone_payload
