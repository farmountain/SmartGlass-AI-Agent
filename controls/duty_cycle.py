"""Duty-cycle scheduler for throttling high-cost pipelines."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from fsm import EngagementState, HandshakeFSM
from fsm.handshake import TimerDriver


def _hz_to_period(hz: float) -> float:
    if hz < 0:
        raise ValueError(f"Frequency must be non-negative, got {hz!r}")
    if hz == 0:
        return 0.0
    return 1.0 / hz


@dataclass
class DutyCycleScheduler:
    """Gate sensor and inference work based on user engagement."""

    timer: TimerDriver
    idle_hz: float = 2.0
    active_hz: float = 0.0
    default_channel: str = "vision"
    _current_period: float = field(init=False)
    _idle_period: float = field(init=False)
    _active_period: float = field(init=False)
    _last_run: Dict[str, float] = field(default_factory=dict, init=False)
    _handshake: Optional[HandshakeFSM] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self._idle_period = _hz_to_period(self.idle_hz)
        self._active_period = _hz_to_period(self.active_hz)
        self._current_period = self._idle_period

    def bind(self, fsm: HandshakeFSM) -> None:
        """Listen to engagement callbacks from ``fsm``."""

        if self._handshake is fsm:
            return
        self._handshake = fsm
        fsm.subscribe_engagement(self._handle_engagement)
        self._handle_engagement(fsm.engagement_state)

    def try_acquire(self, channel: Optional[str] = None) -> bool:
        """Return ``True`` when work is allowed for ``channel`` at this instant."""

        key = channel or self.default_channel
        if self._current_period == 0.0:
            self._last_run[key] = self.timer.now()
            return True
        now = self.timer.now()
        previous = self._last_run.get(key)
        if previous is None or now - previous >= self._current_period:
            self._last_run[key] = now
            return True
        return False

    # ------------------------------------------------------------------
    # Internal helpers

    def _handle_engagement(self, state: EngagementState) -> None:
        if state is EngagementState.ACTIVE:
            self._current_period = self._active_period
            return
        self._current_period = self._idle_period
        self._last_run.clear()
