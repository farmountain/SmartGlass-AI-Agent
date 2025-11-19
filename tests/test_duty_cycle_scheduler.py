from __future__ import annotations

import heapq
from pathlib import Path
from typing import Callable, Iterable, List

import numpy as np

from bench.phone_perf_timeline import (
    TIMELINE_DURATION_S,
    TIMELINE_REQUEST_INTERVAL_S,
    state_for_time,
)
from controls import DutyCycleScheduler
from fsm import EngagementState, HandshakeFSM, HandshakeState, load_handshake_budgets
from rayskillkit import RaySkillKitRuntime


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


def _build_fsm() -> tuple[HandshakeFSM, FakeTimer, float]:
    budgets = load_handshake_budgets(Path("config/ux_budgets.yaml"))
    timer = FakeTimer()
    fsm = HandshakeFSM(timer=timer, budgets=budgets)
    return fsm, timer, budgets.degrade_p50


class _CountingOrt:
    def __init__(self) -> None:
        self.calls = 0

    def infer(self, model_name: str, features: np.ndarray) -> np.ndarray:
        self.calls += 1
        return features


def _simulate_timeline(idle_hz: float) -> tuple[int, List[float]]:
    fsm, timer, _ = _build_fsm()
    scheduler = DutyCycleScheduler(timer, idle_hz=idle_hz, active_hz=0.0)
    runtime = RaySkillKitRuntime(handshake=fsm, scheduler=scheduler)
    ort = _CountingOrt()
    features = np.ones(8, dtype=np.float32)
    fsm.pair()
    fsm.mark_user_idle()
    current_state = EngagementState.IDLE
    latencies: List[float] = []
    pending_start: float | None = None

    request_time = 0.0
    while request_time < TIMELINE_DURATION_S:
        label = state_for_time(request_time)
        target = EngagementState.ACTIVE if label == "active" else EngagementState.IDLE
        if target is not current_state:
            if target is EngagementState.ACTIVE:
                fsm.mark_user_active()
            else:
                fsm.mark_user_idle()
            current_state = target

        timer.advance(request_time - timer.now())
        fsm.heartbeat()
        result = runtime.run_inference(ort, "demo", features)
        if result is None:
            if pending_start is None:
                pending_start = timer.now()
        elif pending_start is not None:
            latencies.append(timer.now() - pending_start)
            pending_start = None

        request_time = round(request_time + TIMELINE_REQUEST_INTERVAL_S, 10)

    return ort.calls, latencies


def test_ready_state_emits_idle_and_active_callbacks() -> None:
    fsm, timer, degrade_p50 = _build_fsm()
    events: List[EngagementState] = []
    fsm.subscribe_engagement(events.append)

    fsm.pair()
    assert events[-1] is EngagementState.IDLE

    fsm.mark_user_active()
    assert events[-1] is EngagementState.ACTIVE

    timer.advance(degrade_p50 + 0.05)
    assert fsm.state is HandshakeState.DEGRADED

    fsm.heartbeat()
    assert fsm.state is HandshakeState.READY
    assert events[-1] is EngagementState.IDLE


def test_scheduler_respects_idle_and_active_rates() -> None:
    fsm, timer, _ = _build_fsm()
    scheduler = DutyCycleScheduler(timer, idle_hz=2.0, active_hz=0.0)
    scheduler.bind(fsm)

    fsm.pair()
    assert scheduler.try_acquire()
    assert not scheduler.try_acquire()

    timer.advance(0.5)
    assert scheduler.try_acquire()

    fsm.mark_user_active()
    assert scheduler.try_acquire()
    assert scheduler.try_acquire()

    fsm.mark_user_idle()
    assert scheduler.try_acquire()
    assert not scheduler.try_acquire()


def test_runtime_gates_camera_and_inference() -> None:
    class Camera:
        def __init__(self) -> None:
            self._frames = [np.zeros((2, 2, 3), dtype=np.float32) for _ in range(3)]

        def camera(self, *, seconds: int = 1) -> Iterable[np.ndarray]:
            yield from (frame.copy() for frame in self._frames)

    class Ort:
        def __init__(self) -> None:
            self.calls: List[str] = []

        def infer(self, model_name: str, features: np.ndarray) -> np.ndarray:
            self.calls.append(model_name)
            return features + 1.0

    fsm, timer, _ = _build_fsm()
    scheduler = DutyCycleScheduler(timer, idle_hz=2.0, active_hz=0.0)
    runtime = RaySkillKitRuntime(handshake=fsm, scheduler=scheduler)

    camera = Camera()
    ort = Ort()

    assert runtime.capture_clip(camera) is None  # not paired yet
    fsm.pair()

    clip = runtime.capture_clip(camera)
    assert clip is not None
    assert runtime.capture_clip(camera) is None

    timer.advance(0.5)
    assert runtime.capture_clip(camera) is not None

    features = np.ones(4, dtype=np.float32)
    assert runtime.run_inference(ort, "demo", features) is None

    fsm.mark_user_active()
    result = runtime.run_inference(ort, "demo", features)
    assert result is not None and np.allclose(result, features + 1.0)
    assert runtime.run_inference(ort, "demo", features) is not None

    fsm.mark_user_idle()
    assert runtime.run_inference(ort, "demo", features) is not None
    assert runtime.run_inference(ort, "demo", features) is None

    timer.advance(0.5)
    assert runtime.run_inference(ort, "demo", features) is not None


def test_duty_cycle_timeline_saves_tokens_and_bounds_latency() -> None:
    baseline_calls, _ = _simulate_timeline(idle_hz=0.0)
    duty_calls, duty_latencies = _simulate_timeline(idle_hz=2.0)

    assert duty_calls <= baseline_calls * 0.5
    assert duty_latencies, "Expected duty-cycle gating to introduce measurable latency"
    allowed_penalty = 0.5  # 1 / idle_hz
    assert max(duty_latencies) <= allowed_penalty + 1e-6
