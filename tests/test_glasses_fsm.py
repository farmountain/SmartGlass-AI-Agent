"""Unit tests for the conversational FSM used by SmartGlass."""

from __future__ import annotations

import asyncio
from typing import Callable, List

from fsm.glasses import (
    GlassesFSM,
    GlassesState,
    InteractionBudgets,
)


class FakeTimerHandle:
    def __init__(self, callback: Callable[[], None]) -> None:
        self.callback = callback
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True


class FakeTimerDriver:
    def __init__(self) -> None:
        self.scheduled: List[Callable[[], None]] = []

    def call_later(self, delay: float, callback: Callable[[], None]) -> FakeTimerHandle:
        # Record the callback but do not run it automatically to keep the test deterministic.
        self.scheduled.append(callback)
        return FakeTimerHandle(callback)


class ImmediateAsyncDriver:
    def create_task(self, coro) -> None:  # type: ignore[override]
        asyncio.run(coro)


def test_happy_path_transitions_without_blocking():
    budgets = InteractionBudgets(listen_timeout=1.0, thinking_timeout=1.0, response_timeout=1.0)
    timer = FakeTimerDriver()
    async_driver = ImmediateAsyncDriver()

    transitions: List[tuple[GlassesState, GlassesState]] = []
    fsm = GlassesFSM(
        timer=timer,
        async_driver=async_driver,
        budgets=budgets,
        listeners=[lambda prev, new: transitions.append((prev, new))],
    )

    assert fsm.state is GlassesState.IDLE

    fsm.wake_word_detected()
    assert fsm.state is GlassesState.LISTENING

    fsm.request_submitted()
    assert fsm.state is GlassesState.THINKING

    fsm.response_ready("ok")
    assert fsm.state is GlassesState.RESPONDING

    fsm.response_complete()
    assert fsm.state is GlassesState.IDLE

    assert transitions == [
        (GlassesState.IDLE, GlassesState.LISTENING),
        (GlassesState.LISTENING, GlassesState.THINKING),
        (GlassesState.THINKING, GlassesState.RESPONDING),
        (GlassesState.RESPONDING, GlassesState.IDLE),
    ]

    # No timer callbacks were auto-triggered, but they were registered for each stage.
    assert len(timer.scheduled) == 3
