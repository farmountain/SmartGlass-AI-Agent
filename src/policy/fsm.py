"""Minimal finite state machine router for policy workflows."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List


@dataclass(frozen=True)
class State:
    """Represents a state within the FSM."""

    name: str
    irreversible: bool = False


@dataclass(frozen=True)
class Event:
    """Represents a transition between two states."""

    name: str
    source: str
    target: str


class FSMRouter:
    """Simple router enforcing confirm-before-irreversible transitions."""

    def __init__(self, states: Iterable[State], events: Iterable[Event], initial_state: str) -> None:
        self._states: Dict[str, State] = {state.name: state for state in states}
        if initial_state not in self._states:
            raise ValueError(f"Unknown initial state '{initial_state}'.")

        self._events: Dict[str, Event] = {event.name: event for event in events}
        self._state: State = self._states[initial_state]
        self._enter_hooks: Dict[str, List[Callable[[State, State, Event], None]]] = {}

    @property
    def state(self) -> State:
        return self._state

    def on_enter_state(self, state_name: str, callback: Callable[[State, State, Event], None]) -> None:
        if state_name not in self._states:
            raise ValueError(f"Unknown state '{state_name}'.")
        hooks = self._enter_hooks.setdefault(state_name, [])
        hooks.append(callback)

    def transition(self, event_name: str, *, confirm: bool = False) -> State:
        if event_name not in self._events:
            raise ValueError(f"Unknown event '{event_name}'.")

        event = self._events[event_name]
        if event.source != self._state.name:
            raise ValueError(
                f"Cannot transition via event '{event_name}' from state '{self._state.name}'."
            )

        target_state = self._states[event.target]
        if target_state.irreversible and not confirm:
            raise PermissionError(
                f"Transition to irreversible state '{target_state.name}' requires confirmation."
            )

        previous_state = self._state
        self._state = target_state
        for callback in self._enter_hooks.get(target_state.name, []):
            callback(previous_state, target_state, event)
        return self._state
