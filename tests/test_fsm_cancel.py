from pathlib import Path
import sys

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


def test_cancel_returns_to_idle_without_irreversible_side_effects():
    router = _build_router()

    executed_hooks = []
    router.on_enter_state("SPEAK", lambda *args: executed_hooks.append("SPEAK"))

    router.transition("WAKE")
    router.transition("FRAME")
    router.transition("FUSED")
    router.transition("CAPTION_READY")
    assert router.state.name == "CONFIRM"

    router.transition("CANCEL")
    assert router.state.name == "IDLE"
    assert executed_hooks == []
