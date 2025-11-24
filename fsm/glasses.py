"""State machine governing SmartGlass conversational loop."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Awaitable, Callable, Iterable, MutableMapping, Optional, Protocol

TransitionListener = Callable[["GlassesState", "GlassesState"], None]


class TimerHandle(Protocol):
    """Minimal protocol for cancellable timer handles."""

    def cancel(self) -> None:  # pragma: no cover - structural typing only
        """Cancel the scheduled callback."""


class TimerDriver(Protocol):
    """Protocol describing the timer hooks required by :class:`GlassesFSM`."""

    def call_later(self, delay: float, callback: Callable[[], None]) -> TimerHandle:  # pragma: no cover
        """Schedule *callback* to be invoked after *delay* seconds."""


class AsyncDriver(Protocol):
    """Protocol used to schedule non-blocking async hooks."""

    def create_task(self, coro: Awaitable[None]) -> None:  # pragma: no cover - structural typing only
        """Schedule *coro* for execution without blocking the caller."""


class GlassesState(Enum):
    """Conversational states for the wearable."""

    IDLE = auto()
    LISTENING = auto()
    THINKING = auto()
    RESPONDING = auto()
    ERROR = auto()


class GlassesEvent(Enum):
    """Supported triggers for the conversational FSM."""

    WAKE_WORD_DETECTED = auto()
    BUTTON_TAPPED = auto()
    NETWORK_ERROR = auto()
    TIMEOUT = auto()
    RESPONSE_READY = auto()
    REQUEST_SUBMITTED = auto()


@dataclass(frozen=True)
class InteractionBudgets:
    """Latency budgets (in seconds) for the conversational loop."""

    listen_timeout: float
    thinking_timeout: float
    response_timeout: float

    def __post_init__(self) -> None:
        for field_name in ("listen_timeout", "thinking_timeout", "response_timeout"):
            value = getattr(self, field_name)
            if value <= 0:
                raise ValueError(f"{field_name} must be positive, got {value!r}")


def _noop_async(*_: object, **__: object) -> Awaitable[None]:
    async def _inner() -> None:
        return None

    return _inner()


@dataclass
class GlassesHooks:
    """Async hooks used to interact with hardware without blocking."""

    start_audio_stream: Callable[[], Awaitable[None]] = _noop_async
    stop_audio_stream: Callable[[], Awaitable[None]] = _noop_async
    start_tts: Callable[[str], Awaitable[None]] = _noop_async
    stop_tts: Callable[[], Awaitable[None]] = _noop_async
    show_overlay: Callable[[GlassesState], Awaitable[None]] = _noop_async
    hide_overlay: Callable[[GlassesState], Awaitable[None]] = _noop_async


class GlassesFSM:
    """Deterministic FSM coordinating the conversational experience."""

    def __init__(
        self,
        *,
        timer: TimerDriver,
        async_driver: AsyncDriver,
        budgets: InteractionBudgets,
        listeners: Optional[Iterable[TransitionListener]] = None,
        hooks: Optional[GlassesHooks] = None,
    ) -> None:
        self._timer = timer
        self._async = async_driver
        self._budgets = budgets
        self._listeners = list(listeners or [])
        self._hooks = hooks or GlassesHooks()
        self._state = GlassesState.IDLE
        self._last_error_reason: Optional[str] = None
        self._active_timers: MutableMapping[str, TimerHandle] = {}

    @property
    def state(self) -> GlassesState:
        """Return the current conversational state."""

        return self._state

    @property
    def last_error_reason(self) -> Optional[str]:
        """Most recent error description, if any."""

        return self._last_error_reason

    def subscribe(self, listener: TransitionListener) -> None:
        """Subscribe to future state transitions."""

        self._listeners.append(listener)

    # ------------------------------------------------------------------
    # Public event handlers

    def wake_word_detected(self) -> None:
        self._guard_transition(GlassesEvent.WAKE_WORD_DETECTED, {GlassesState.IDLE})
        self._enter_listening()

    def button_tapped(self) -> None:
        if self._state is GlassesState.IDLE:
            self._enter_listening()
            return
        if self._state is GlassesState.RESPONDING:
            self.response_complete()
            return
        raise RuntimeError("button_tapped() is not valid in the current state")

    def request_submitted(self) -> None:
        self._guard_transition(GlassesEvent.REQUEST_SUBMITTED, {GlassesState.LISTENING})
        self._enter_thinking()

    def response_ready(self, response_text: str) -> None:
        self._guard_transition(GlassesEvent.RESPONSE_READY, {GlassesState.THINKING})
        self._enter_responding(response_text)

    def response_complete(self) -> None:
        if self._state is not GlassesState.RESPONDING:
            raise RuntimeError("response_complete() can only be called from RESPONDING")
        self._cancel_all_timers()
        self._schedule_hook(self._hooks.stop_tts)
        self._transition_to(GlassesState.IDLE)

    def network_error(self) -> None:
        if self._state is GlassesState.ERROR:
            return
        if self._state is GlassesState.IDLE:
            return
        self._enter_error("Network error")

    def timeout(self) -> None:
        if self._state in {GlassesState.IDLE, GlassesState.ERROR}:
            return
        self._enter_error("Timeout")

    def reset(self) -> None:
        self._cancel_all_timers()
        self._transition_to(GlassesState.IDLE)

    # ------------------------------------------------------------------
    # State entry helpers

    def _enter_listening(self) -> None:
        self._cancel_all_timers()
        self._transition_to(GlassesState.LISTENING)
        self._schedule_hook(self._hooks.show_overlay, GlassesState.LISTENING)
        self._schedule_hook(self._hooks.start_audio_stream)
        self._set_timer("listen_timeout", self._budgets.listen_timeout, self.timeout)

    def _enter_thinking(self) -> None:
        self._cancel_all_timers()
        self._schedule_hook(self._hooks.stop_audio_stream)
        self._transition_to(GlassesState.THINKING)
        self._schedule_hook(self._hooks.show_overlay, GlassesState.THINKING)
        self._set_timer("thinking_timeout", self._budgets.thinking_timeout, self.timeout)

    def _enter_responding(self, response_text: str) -> None:
        self._cancel_all_timers()
        self._transition_to(GlassesState.RESPONDING)
        self._schedule_hook(self._hooks.show_overlay, GlassesState.RESPONDING)
        self._schedule_hook(self._hooks.start_tts, response_text)
        self._set_timer("response_timeout", self._budgets.response_timeout, self.timeout)

    def _enter_error(self, reason: str) -> None:
        self._cancel_all_timers()
        self._last_error_reason = reason
        self._schedule_hook(self._hooks.stop_audio_stream)
        self._schedule_hook(self._hooks.stop_tts)
        self._transition_to(GlassesState.ERROR)
        self._schedule_hook(self._hooks.show_overlay, GlassesState.ERROR)

    # ------------------------------------------------------------------
    # Timer helpers

    def _set_timer(self, key: str, delay: float, callback: Callable[[], None]) -> None:
        if delay <= 0:
            raise ValueError("Timer delay must be positive")
        self._cancel_timer(key)
        handle = self._timer.call_later(delay, self._wrap_timer_callback(key, callback))
        self._active_timers[key] = handle

    def _wrap_timer_callback(self, key: str, callback: Callable[[], None]) -> Callable[[], None]:
        def runner() -> None:
            self._active_timers.pop(key, None)
            callback()

        return runner

    def _cancel_timer(self, key: str) -> None:
        handle = self._active_timers.pop(key, None)
        if handle is not None:
            handle.cancel()

    def _cancel_all_timers(self) -> None:
        for handle in list(self._active_timers.values()):
            handle.cancel()
        self._active_timers.clear()

    # ------------------------------------------------------------------
    # Book-keeping utilities

    def _transition_to(self, new_state: GlassesState) -> None:
        if new_state is self._state:
            return
        previous = self._state
        self._schedule_hook(self._hooks.hide_overlay, previous)
        self._state = new_state
        for listener in self._listeners:
            listener(previous, new_state)

    def _guard_transition(self, event: GlassesEvent, allowed_states: set[GlassesState]) -> None:
        if self._state not in allowed_states:
            raise RuntimeError(f"{event.name} is not valid from {self._state.name}")

    def _schedule_hook(self, hook: Callable[..., Awaitable[None]], *args: object) -> None:
        try:
            coro = hook(*args)
        except Exception as exc:  # pragma: no cover - defensive: hook misconfiguration
            raise RuntimeError("Hook invocation failed") from exc
        self._async.create_task(coro)
