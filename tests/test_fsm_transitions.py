from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from policy.fsm import Event, FSMRouter, State


def build_router():
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
    return router


def test_golden_path_transitions():
    router = build_router()
    entered = []

    router.on_enter_state("PREPARING", lambda prev, cur, event: entered.append((prev.name, cur.name)))
    router.on_enter_state("EXECUTING", lambda prev, cur, event: entered.append((prev.name, cur.name)))

    assert router.state.name == "IDLE"

    router.transition("start")
    assert router.state.name == "PREPARING"

    router.transition("execute", confirm=True)
    assert router.state.name == "EXECUTING"

    assert entered == [("IDLE", "PREPARING"), ("PREPARING", "EXECUTING")]
