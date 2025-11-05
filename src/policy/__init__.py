"""Policy factories and helpers for the SmartGlass agent."""

from __future__ import annotations

from src.fusion import ConfidenceFusion

from .fsm import Event, FSMRouter, State

__all__ = [
    "Event",
    "State",
    "FSMRouter",
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
        State("RESPONDING", irreversible=True),
    ]
    events = [
        Event("activate", source="IDLE", target="LISTENING"),
        Event("observe", source="LISTENING", target="ANALYSING"),
        Event("respond", source="ANALYSING", target="RESPONDING"),
    ]

    router = FSMRouter(states, events, initial_state="IDLE")
    fusion = ConfidenceFusion()
    return router, fusion
