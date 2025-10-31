from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from policy.fsm import Event, FSMRouter, State


def test_cancel_returns_to_idle_without_irreversible_side_effects():
    states = [
        State("IDLE"),
        State("PREPARING"),
        State("EXECUTING", irreversible=True),
    ]
    events = [
        Event("start", "IDLE", "PREPARING"),
        Event("cancel", "PREPARING", "IDLE"),
        Event("execute", "PREPARING", "EXECUTING"),
    ]
    router = FSMRouter(states, events, initial_state="IDLE")

    executed_hooks = []
    router.on_enter_state("EXECUTING", lambda prev, cur, event: executed_hooks.append(event.name))

    router.transition("start")
    assert router.state.name == "PREPARING"

    router.transition("cancel")
    assert router.state.name == "IDLE"
    assert executed_hooks == []
