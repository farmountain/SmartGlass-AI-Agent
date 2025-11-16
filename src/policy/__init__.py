"""Policy factories and helpers for the SmartGlass agent."""

from __future__ import annotations

from src.fusion import ConfidenceFusion

from .fsm import Event, FSMRouter, State
from .permissions import PermissionDecision, can_capture

__all__ = [
    "Event",
    "State",
    "FSMRouter",
    "PermissionDecision",
    "can_capture",
    "get_default_policy",
]


def get_default_policy() -> tuple[FSMRouter, ConfidenceFusion]:
    """Return the default policy primitives.

    The router encapsulates the finite-state machine transitions for the agent,
    while the fusion object is used to combine multi-sensor confidence scores.
    """

    states = [
        State("IDLE"),
        State("LISTENING"),
        State("ANALYSING"),
        State("CONFIRM"),
        State("PAUSE"),
        State("DENY", irreversible=True),
        State("RESPONDING", irreversible=True),
    ]
    events = [
        Event("activate", source="IDLE", target="LISTENING"),
        Event("observe", source="LISTENING", target="ANALYSING"),
        Event("confirm", source="ANALYSING", target="CONFIRM"),
        Event("respond", source="CONFIRM", target="RESPONDING"),
        Event("pause", source=("LISTENING", "ANALYSING", "CONFIRM"), target="PAUSE"),
        Event("resume", source="PAUSE", target="LISTENING"),
        Event("deny", source=("IDLE", "LISTENING", "ANALYSING", "CONFIRM", "PAUSE"), target="DENY"),
    ]

    router = FSMRouter(states, events, initial_state="IDLE")
    fusion = ConfidenceFusion()
    return router, fusion
