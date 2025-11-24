"""Demonstrate the conversational FSM without external services.

This script walks through a wake-word triggered interaction followed by a short
query and response. All transitions are logged synchronously so the example can
run without real timers or hardware hooks.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Callable, List

from fsm.glasses import (
    GlassesFSM,
    GlassesHooks,
    GlassesState,
    InteractionBudgets,
)


class FakeTimerHandle:
    """Simple cancellable handle for scheduled callbacks."""

    def __init__(self, callback: Callable[[], None]) -> None:
        self.callback = callback
        self.cancelled = False

    def cancel(self) -> None:  # pragma: no cover - trivial
        self.cancelled = True


class FakeTimerDriver:
    """Timer driver that records scheduled callbacks without waiting."""

    def __init__(self) -> None:
        self.invocations: List[str] = []
        self.handles: List[FakeTimerHandle] = []

    def call_later(self, delay: float, callback: Callable[[], None]) -> FakeTimerHandle:
        handle = FakeTimerHandle(callback)
        self.invocations.append(f"Timer scheduled for {delay:.2f}s")
        self.handles.append(handle)
        return handle

    def fire_all(self) -> None:
        """Manually trigger any queued callbacks for demonstration purposes."""
        for handle in list(self.handles):
            if not handle.cancelled:
                handle.callback()


class ImmediateAsyncDriver:
    """Async driver that runs coroutines to completion immediately."""

    def create_task(self, coro) -> None:  # type: ignore[override]
        asyncio.run(coro)


@dataclass
class LoggingHooks(GlassesHooks):
    """Hooks that print lifecycle events for visibility."""

    def show_overlay(self, state: GlassesState):  # type: ignore[override]
        async def _run() -> None:
            print(f"Overlay ON for {state.name}")

        return _run()

    def hide_overlay(self, state: GlassesState):  # type: ignore[override]
        async def _run() -> None:
            print(f"Overlay OFF for {state.name}")

        return _run()

    def start_audio_stream(self):  # type: ignore[override]
        async def _run() -> None:
            print("Mic streaming started")

        return _run()

    def stop_audio_stream(self):  # type: ignore[override]
        async def _run() -> None:
            print("Mic streaming stopped")

        return _run()

    def start_tts(self, text: str):  # type: ignore[override]
        async def _run() -> None:
            print(f"TTS speaking: {text}")

        return _run()

    def stop_tts(self):  # type: ignore[override]
        async def _run() -> None:
            print("TTS stopped")

        return _run()


def main() -> None:
    budgets = InteractionBudgets(listen_timeout=2.0, thinking_timeout=2.0, response_timeout=2.0)
    timer = FakeTimerDriver()
    async_driver = ImmediateAsyncDriver()
    fsm = GlassesFSM(timer=timer, async_driver=async_driver, budgets=budgets, hooks=LoggingHooks())

    def log_transition(prev: GlassesState, new: GlassesState) -> None:
        print(f"Transition: {prev.name} -> {new.name}")

    fsm.subscribe(log_transition)

    print("Wake word detected…")
    fsm.wake_word_detected()

    print("Submitting short query…")
    fsm.request_submitted()

    print("Assistant responded…")
    fsm.response_ready("Here is your answer!")

    print("Response delivered; returning to idle.")
    fsm.response_complete()


if __name__ == "__main__":
    main()
