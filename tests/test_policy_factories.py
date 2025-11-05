"""Smoke tests for policy and perception factory exports."""

from src.fusion import ConfidenceFusion
from src.perception import (
    ASRStream,
    EnergyVAD,
    VQEncoder,
    get_default_asr,
    get_default_keyframer,
    get_default_ocr,
    get_default_vad,
    get_default_vq,
    select_keyframes,
    text_and_boxes,
)
from src.policy import FSMRouter, get_default_policy


def test_get_default_policy_exports_primitives():
    router, fusion = get_default_policy()

    assert isinstance(router, FSMRouter)
    assert isinstance(fusion, ConfidenceFusion)


def test_perception_factories_smoke():
    assert get_default_keyframer() is select_keyframes

    vad = get_default_vad()
    assert isinstance(vad, EnergyVAD)

    asr = get_default_asr()
    assert isinstance(asr, ASRStream)

    vq = get_default_vq()
    assert isinstance(vq, VQEncoder)

    ocr = get_default_ocr()
    assert ocr is text_and_boxes
