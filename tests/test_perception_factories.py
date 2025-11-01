"""Smoke tests for perception factory helpers."""

import src.perception.ocr as ocr
from src.perception import (
    VQEncoder,
    get_default_keyframer,
    get_default_ocr,
    get_default_vq,
    select_keyframes,
)


def test_get_default_keyframer_returns_select_keyframes():
    assert get_default_keyframer() is select_keyframes


def test_get_default_vq_returns_vqencoder_instance():
    encoder = get_default_vq()
    assert isinstance(encoder, VQEncoder)


def test_get_default_ocr_returns_text_and_boxes():
    assert get_default_ocr() is ocr.text_and_boxes
