from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from policy.fsm import Event, FSMRouter, State


def _build_router() -> FSMRouter:
    states = [
        State("IDLE"),
        State("PERCEIVE"),
        State("FUSE"),
        State("CAPTION"),
        State("SPEAK", irreversible=True),
        State("CONFIRM"),
    ]
    events = [
        Event("WAKE", "IDLE", "PERCEIVE"),
        Event("FRAME", "PERCEIVE", "FUSE"),
        Event("FUSED", "FUSE", "CAPTION"),
        Event("CAPTION_READY", "CAPTION", "CONFIRM"),
        Event("CONFIRM_YES", "CONFIRM", "SPEAK"),
        Event("CONFIRM_NO", "CONFIRM", "CAPTION"),
        Event("CANCEL", ("PERCEIVE", "FUSE", "CAPTION", "CONFIRM", "SPEAK"), "IDLE"),
        Event("TIMEOUT", "CONFIRM", "IDLE"),
        Event("SPEAK_DONE", "SPEAK", "IDLE"),
    ]
    return FSMRouter(states, events, initial_state="IDLE")


def test_confirm_required_for_irreversible_transition():
    router = _build_router()

    router.transition("WAKE")
    router.transition("FRAME")
    router.transition("FUSED")
    router.transition("CAPTION_READY")
    assert router.state.name == "CONFIRM"

    with pytest.raises(PermissionError):
        router.transition("CONFIRM_YES")

    assert router.state.name == "CONFIRM"

    router.transition("CONFIRM_YES", confirm=True)
    assert router.state.name == "SPEAK"

    router.transition("SPEAK_DONE")
    assert router.state.name == "IDLE"

    router.transition("WAKE")
    router.transition("FRAME")
    router.transition("FUSED")
    router.transition("CAPTION_READY")
    router.transition("TIMEOUT")
    assert router.state.name == "IDLE"
