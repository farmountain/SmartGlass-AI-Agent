"""Policy factories and helpers for the SmartGlass agent."""

from __future__ import annotations

from dataclasses import dataclass

from src.fusion import ConfidenceFusion

from .fsm import Event, FSMRouter, State

__all__ = [
    "Event",
    "State",
    "FSMRouter",
    "PolicyBundle",
    "get_default_policy",
]


@dataclass(frozen=True)
class PolicyBundle:
    """Container bundling policy-level primitives."""

    router: FSMRouter
    fusion: ConfidenceFusion


def get_default_policy() -> PolicyBundle:
    """Return the default policy bundle used by the SmartGlass agent."""

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
    return PolicyBundle(router=router, fusion=fusion)
