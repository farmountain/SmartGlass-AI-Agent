"""Finite state machine router with confirmation-aware transitions."""
from __future__ import annotations

from dataclasses import dataclass
from inspect import Parameter, signature
from typing import Callable, Dict, Iterable, List, Tuple, Union


@dataclass(frozen=True)
class State:
    """Represents a state within the FSM."""

    name: str
    irreversible: bool = False


@dataclass(frozen=True)
class Event:
    """Represents a transition between two states."""

    name: str
    source: Union[str, Iterable[str]]
    target: str

    def __post_init__(self) -> None:
        raw_source = self.source
        if isinstance(raw_source, str):
            sources: Tuple[str, ...] = (raw_source,)
        else:
            sources = tuple(raw_source)
        if not sources:
            raise ValueError(f"Event '{self.name}' must have at least one source state.")
        object.__setattr__(self, "sources", sources)


class FSMRouter:
    """Simple router enforcing confirm-before-irreversible transitions."""

    def __init__(self, states: Iterable[State], events: Iterable[Event], initial_state: str) -> None:
        self._states: Dict[str, State] = {state.name: state for state in states}
        if initial_state not in self._states:
            raise ValueError(f"Unknown initial state '{initial_state}'.")

        self._events: Dict[str, Event] = {}
        for event in events:
            if event.name in self._events:
                raise ValueError(f"Duplicate event '{event.name}' encountered.")
            for source in event.sources:
                if source not in self._states:
                    raise ValueError(
                        f"Event '{event.name}' references unknown source state '{source}'."
                    )
            if event.target not in self._states:
                raise ValueError(
                    f"Event '{event.name}' targets unknown state '{event.target}'."
                )
            self._events[event.name] = event

        self._state: State = self._states[initial_state]
        self._enter_hooks: Dict[str, List[Callable[..., None]]] = {}
        self._transition_counts: Dict[str, int] = {event.name: 0 for event in self._events.values()}

    @property
    def state(self) -> State:
        return self._state

    def on_enter_state(self, state_name: str, callback: Callable[..., None]) -> None:
        if state_name not in self._states:
            raise ValueError(f"Unknown state '{state_name}'.")
        hooks = self._enter_hooks.setdefault(state_name, [])
        hooks.append(callback)

    @property
    def transition_counts(self) -> Dict[str, int]:
        return dict(self._transition_counts)

    def _callback_accepts_payload(self, callback: Callable[..., None]) -> bool:
        try:
            sig = signature(callback)
        except (TypeError, ValueError):
            return True
        params = list(sig.parameters.values())
        if not params:
            return False
        last_param = params[-1]
        return last_param.kind in (
            Parameter.VAR_POSITIONAL,
            Parameter.VAR_KEYWORD,
        ) or len(params) >= 4

    def transition(self, event_name: str, **payload) -> State:
        if event_name not in self._events:
            raise ValueError(f"Unknown event '{event_name}'.")

        event = self._events[event_name]
        if self._state.name not in event.sources:
            raise ValueError(
                f"Cannot transition via event '{event_name}' from state '{self._state.name}'."
            )

        target_state = self._states[event.target]
        confirm_flag = bool(payload.pop("confirm", False))
        if target_state.irreversible and not confirm_flag:
            raise PermissionError(
                f"Transition to irreversible state '{target_state.name}' requires confirmation."
            )

        previous_state = self._state
        self._state = target_state
        self._transition_counts[event_name] = self._transition_counts.get(event_name, 0) + 1

        callback_payload = dict(payload)
        callback_payload.setdefault("confirm", confirm_flag)
        for callback in self._enter_hooks.get(target_state.name, []):
            if self._callback_accepts_payload(callback):
                callback(previous_state, target_state, event, callback_payload)
            else:
                callback(previous_state, target_state, event)
        return self._state
