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


def test_default_policy_supports_permission_transitions():
    router, _ = get_default_policy()

    assert router.state.name == "IDLE"
    router.transition("activate")
    assert router.state.name == "LISTENING"
    router.transition("pause")
    assert router.state.name == "PAUSE"
    router.transition("resume")
    router.transition("observe")
    router.transition("confirm")
    router.transition("respond", confirm=True)
    assert router.state.name == "RESPONDING"

    router2, _ = get_default_policy()
    router2.transition("deny", confirm=True)
    assert router2.state.name == "DENY"


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
