"""State machine for managing the SmartGlass handshake lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Dict, Iterable, MutableMapping, Optional, Protocol


class TimerHandle(Protocol):
    """Minimal protocol for cancellable timer handles."""

    def cancel(self) -> None:  # pragma: no cover - structural typing only
        """Cancel the scheduled callback."""


class TimerDriver(Protocol):
    """Protocol describing the timer hooks required by :class:`HandshakeFSM`."""

    def now(self) -> float:  # pragma: no cover - structural typing only
        """Return the current monotonic timestamp."""

    def call_later(self, delay: float, callback: Callable[[], None]) -> TimerHandle:  # pragma: no cover
        """Schedule *callback* to be invoked after *delay* seconds."""


class HandshakeState(Enum):
    """Lifecycle stages of the wearable connection."""

    UNPAIRED = auto()
    READY = auto()
    DEGRADED = auto()
    RECONNECTING = auto()


class EngagementState(Enum):
    """User engagement mode while the wearable is READY."""

    IDLE = auto()
    ACTIVE = auto()


@dataclass(frozen=True)
class HandshakeBudgets:
    """Latency budgets (in seconds) for the handshake state machine."""

    degrade_p50: float
    degrade_p95: float
    reconnect_p50: float
    reconnect_p95: float

    def __post_init__(self) -> None:
        for field_name in ("degrade_p50", "degrade_p95", "reconnect_p50", "reconnect_p95"):
            value = getattr(self, field_name)
            if value <= 0:
                raise ValueError(f"{field_name} must be positive, got {value!r}")

        if self.degrade_p50 > self.degrade_p95:
            raise ValueError("degrade_p50 cannot exceed degrade_p95")
        if self.reconnect_p50 > self.reconnect_p95:
            raise ValueError("reconnect_p50 cannot exceed reconnect_p95")


TransitionListener = Callable[[HandshakeState, HandshakeState], None]
EngagementListener = Callable[[EngagementState], None]


class HandshakeFSM:
    """Finite state machine coordinating wearer's connection health.

    The FSM is intentionally deterministic so that product and UX teams can
    reason about timing guarantees. State transitions are driven by the
    injected :class:`TimerDriver` which enables deterministic simulations in
    unit tests and integration with event loops in production.
    """

    def __init__(
        self,
        *,
        timer: TimerDriver,
        budgets: HandshakeBudgets,
        listeners: Optional[Iterable[TransitionListener]] = None,
        engagement_listeners: Optional[Iterable[EngagementListener]] = None,
    ) -> None:
        self._timer = timer
        self._budgets = budgets
        self._listeners = list(listeners or [])
        self._engagement_listeners = list(engagement_listeners or [])
        self._state = HandshakeState.UNPAIRED
        self._engagement_state = EngagementState.IDLE
        self._active_timers: MutableMapping[str, TimerHandle] = {}

    @property
    def state(self) -> HandshakeState:
        """Current handshake state."""

        return self._state

    def subscribe(self, listener: TransitionListener) -> None:
        """Subscribe to future state transitions."""

        self._listeners.append(listener)

    def subscribe_engagement(self, listener: EngagementListener) -> None:
        """Subscribe to user engagement transitions."""

        self._engagement_listeners.append(listener)
        listener(self._engagement_state)

    @property
    def engagement_state(self) -> EngagementState:
        """Current user engagement mode."""

        return self._engagement_state

    def mark_user_active(self) -> None:
        """Record that the user interacted with the wearable."""

        self._set_engagement_state(EngagementState.ACTIVE)

    def mark_user_idle(self) -> None:
        """Record that the wearable no longer has user engagement."""

        self._set_engagement_state(EngagementState.IDLE)

    def reset(self) -> None:
        """Return the FSM to the :attr:`~HandshakeState.UNPAIRED` state."""

        self._cancel_all_timers()
        self._transition_to(HandshakeState.UNPAIRED)

    def pair(self) -> None:
        """Enter the :attr:`~HandshakeState.READY` state."""

        if self._state is not HandshakeState.UNPAIRED:
            raise RuntimeError("pair() can only be called from UNPAIRED")
        self._transition_to(HandshakeState.READY)
        self._arm_degrade_timers()

    def heartbeat(self) -> None:
        """Record a healthy heartbeat from the device.

        The heartbeat keeps the wearable in the READY state and restarts the
        degrade timers. If the device was degraded, a heartbeat will immediately
        restore the READY state.
        """

        if self._state is HandshakeState.UNPAIRED:
            return

        if self._state is HandshakeState.RECONNECTING:
            # Once reconnecting, a full re-handshake is required via
            # :meth:`reconnected`.
            return

        if self._state is HandshakeState.DEGRADED:
            self._transition_to(HandshakeState.READY)

        self._arm_degrade_timers()

    def reconnected(self) -> None:
        """Signal that the reconnect handshake completed successfully."""

        if self._state is not HandshakeState.RECONNECTING:
            raise RuntimeError("reconnected() can only be called from RECONNECTING")
        self._transition_to(HandshakeState.READY)
        self._arm_degrade_timers()

    # ------------------------------------------------------------------
    # Timer orchestration helpers

    def _arm_degrade_timers(self) -> None:
        self._cancel_timer("reconnect_primary")
        self._cancel_timer("reconnect_guard")

        self._set_timer("degrade_primary", self._budgets.degrade_p50, self._enter_degraded)
        self._set_timer("degrade_guard", self._budgets.degrade_p95, self._force_degraded)

    def _arm_reconnect_timers(self) -> None:
        self._cancel_timer("degrade_primary")
        self._cancel_timer("degrade_guard")

        self._set_timer("reconnect_primary", self._budgets.reconnect_p50, self._enter_reconnecting)
        self._set_timer("reconnect_guard", self._budgets.reconnect_p95, self._force_reconnecting)

    def _set_timer(self, key: str, delay: float, callback: Callable[[], None]) -> None:
        if delay <= 0:
            raise ValueError("Timer delay must be positive")
        self._cancel_timer(key)

        def runner() -> None:
            self._active_timers.pop(key, None)
            callback()

        handle = self._timer.call_later(delay, runner)
        self._active_timers[key] = handle

    def _cancel_timer(self, key: str) -> None:
        handle = self._active_timers.pop(key, None)
        if handle is not None:
            handle.cancel()

    def _cancel_all_timers(self) -> None:
        for handle in list(self._active_timers.values()):
            handle.cancel()
        self._active_timers.clear()

    # ------------------------------------------------------------------
    # State transitions triggered by timers

    def _enter_degraded(self) -> None:
        if self._state is not HandshakeState.READY:
            return
        self._transition_to(HandshakeState.DEGRADED)
        self._arm_reconnect_timers()

    def _force_degraded(self) -> None:
        if self._state is HandshakeState.DEGRADED:
            return
        self._enter_degraded()

    def _enter_reconnecting(self) -> None:
        if self._state is HandshakeState.RECONNECTING:
            return
        self._transition_to(HandshakeState.RECONNECTING)
        self._cancel_timer("reconnect_guard")

    def _force_reconnecting(self) -> None:
        if self._state is HandshakeState.RECONNECTING:
            return
        self._enter_reconnecting()

    # ------------------------------------------------------------------
    # Book-keeping utilities

    def _transition_to(self, new_state: HandshakeState) -> None:
        if new_state is self._state:
            return
        previous = self._state
        self._state = new_state
        for listener in self._listeners:
            listener(previous, new_state)
        if new_state is not HandshakeState.READY:
            self._engagement_state = EngagementState.IDLE
            return
        # When READY is reached without explicit engagement the wearable is idle.
        self._emit_engagement()

    def _set_engagement_state(self, state: EngagementState) -> None:
        if self._engagement_state is state:
            return
        self._engagement_state = state
        self._emit_engagement()

    def _emit_engagement(self) -> None:
        if self._state is not HandshakeState.READY:
            return
        for listener in self._engagement_listeners:
            listener(self._engagement_state)


def load_handshake_budgets(config_path: Path) -> HandshakeBudgets:
    """Load the UX handshake budgets from ``config/ux_budgets.yaml``.

    The project intentionally keeps the file format simple, so a minimal parser
    is sufficient and avoids introducing additional runtime dependencies.
    """

    text = config_path.read_text(encoding="utf-8")
    in_handshake_block = False
    values: Dict[str, float] = {}

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.endswith(":"):
            in_handshake_block = stripped[:-1] == "handshake"
            continue
        if not in_handshake_block:
            continue
        if ":" not in stripped:
            continue
        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        try:
            values[key] = float(raw_value)
        except ValueError as exc:  # pragma: no cover - config error path
            raise ValueError(f"Invalid numeric value for {key!r}: {raw_value!r}") from exc

    expected_keys = {"degrade_p50", "degrade_p95", "reconnect_p50", "reconnect_p95"}
    missing = expected_keys - values.keys()
    if missing:  # pragma: no cover - configuration error path
        raise KeyError(f"Missing handshake budget keys: {', '.join(sorted(missing))}")

    return HandshakeBudgets(
        degrade_p50=values["degrade_p50"],
        degrade_p95=values["degrade_p95"],
        reconnect_p50=values["reconnect_p50"],
        reconnect_p95=values["reconnect_p95"],
    )
