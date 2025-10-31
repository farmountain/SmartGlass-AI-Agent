from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from policy.fsm import Event, FSMRouter, State


def test_confirm_required_for_irreversible_transition():
    states = [
        State("IDLE"),
        State("PREPARING"),
        State("EXECUTING", irreversible=True),
    ]
    events = [
        Event("start", "IDLE", "PREPARING"),
        Event("execute", "PREPARING", "EXECUTING"),
    ]
    router = FSMRouter(states, events, initial_state="IDLE")

    router.transition("start")
    with pytest.raises(PermissionError):
        router.transition("execute")

    router.transition("execute", confirm=True)
    assert router.state.name == "EXECUTING"
