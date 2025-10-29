from __future__ import annotations

import heapq
from pathlib import Path
from typing import Callable, List
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fsm import HandshakeBudgets, HandshakeFSM, HandshakeState, load_handshake_budgets


class FakeTimerHandle:
    def __init__(self, callback: Callable[[], None], deadline: float) -> None:
        self._callback = callback
        self.deadline = deadline
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True

    def __lt__(self, other: "FakeTimerHandle") -> bool:
        return self.deadline < other.deadline

    def fire(self) -> None:
        if not self.cancelled:
            self._callback()


class FakeTimer:
    def __init__(self) -> None:
        self._now = 0.0
        self._queue: List[FakeTimerHandle] = []

    def now(self) -> float:
        return self._now

    def call_later(self, delay: float, callback: Callable[[], None]) -> FakeTimerHandle:
        handle = FakeTimerHandle(callback, self._now + delay)
        heapq.heappush(self._queue, handle)
        return handle

    def advance(self, delta: float) -> None:
        self._now += delta
        while self._queue and self._queue[0].deadline <= self._now:
            handle = heapq.heappop(self._queue)
            handle.fire()


def load_budgets() -> HandshakeBudgets:
    config_path = Path("config/ux_budgets.yaml")
    return load_handshake_budgets(config_path)


def test_heartbeat_loss_triggers_degrade_and_reconnect_within_budgets() -> None:
    budgets = load_budgets()
    timer = FakeTimer()
    fsm = HandshakeFSM(timer=timer, budgets=budgets)

    fsm.pair()
    assert fsm.state is HandshakeState.READY

    degrade_slack = max((budgets.degrade_p95 - budgets.degrade_p50) / 2, 1e-3)
    reconnect_slack = max((budgets.reconnect_p95 - budgets.reconnect_p50) / 2, 1e-3)
    epsilon = min(0.01, budgets.degrade_p50 / 4, budgets.reconnect_p50 / 4, degrade_slack, reconnect_slack)
    if epsilon <= 0:
        epsilon = 1e-3
    pre_degrade = max(budgets.degrade_p50 - epsilon, 0.0)
    if pre_degrade:
        timer.advance(pre_degrade)
    assert fsm.state is HandshakeState.READY

    timer.advance(2 * epsilon)
    assert fsm.state is HandshakeState.DEGRADED
    degrade_time = timer.now()
    assert budgets.degrade_p50 <= degrade_time <= budgets.degrade_p95

    pre_reconnect = max(budgets.reconnect_p50 - epsilon, 0.0)
    if pre_reconnect:
        timer.advance(pre_reconnect)
    assert fsm.state is HandshakeState.DEGRADED

    timer.advance(2 * epsilon)
    assert fsm.state is HandshakeState.RECONNECTING
    reconnect_elapsed = timer.now() - degrade_time
    assert budgets.reconnect_p50 <= reconnect_elapsed <= budgets.reconnect_p95


def test_heartbeat_resets_degrade_budget() -> None:
    budgets = load_budgets()
    timer = FakeTimer()
    fsm = HandshakeFSM(timer=timer, budgets=budgets)

    fsm.pair()
    half_window = budgets.degrade_p50 / 2
    timer.advance(half_window)
    fsm.heartbeat()

    timer.advance(half_window)
    assert fsm.state is HandshakeState.READY

    timer.advance(half_window + 0.02)
    assert fsm.state is HandshakeState.DEGRADED
