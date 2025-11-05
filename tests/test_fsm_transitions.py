from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from policy.fsm import Event, FSMRouter, State


def build_router() -> FSMRouter:
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


def test_golden_path_transitions():
    router = build_router()
    entered_payloads = {}

    def record_payload(prev, cur, event, payload):
        entered_payloads[cur.name] = {
            "from": prev.name,
            "event": event.name,
            "payload": payload,
        }

    router.on_enter_state("FUSE", record_payload)
    router.on_enter_state("SPEAK", record_payload)

    assert router.state.name == "IDLE"

    router.transition("WAKE")
    router.transition("FRAME", frame_id=42)
    router.transition("FUSED")
    router.transition("CAPTION_READY")
    router.transition("CONFIRM_YES", confirm=True, speaker="demo")
    router.transition("SPEAK_DONE")

    assert router.state.name == "IDLE"

    fuse_payload = entered_payloads["FUSE"]
    assert fuse_payload == {
        "from": "PERCEIVE",
        "event": "FRAME",
        "payload": {"frame_id": 42, "confirm": False},
    }

    speak_payload = entered_payloads["SPEAK"]
    assert speak_payload == {
        "from": "CONFIRM",
        "event": "CONFIRM_YES",
        "payload": {"speaker": "demo", "confirm": True},
    }

    assert router.transition_counts == {
        "WAKE": 1,
        "FRAME": 1,
        "FUSED": 1,
        "CAPTION_READY": 1,
        "CONFIRM_YES": 1,
        "CONFIRM_NO": 0,
        "CANCEL": 0,
        "TIMEOUT": 0,
        "SPEAK_DONE": 1,
    }
