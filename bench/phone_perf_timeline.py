"""Deterministic timeline shared between tests and phone perf bench."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List


@dataclass(frozen=True)
class TimelineSlice:
    """Represents a contiguous engagement segment in seconds."""

    start_s: float
    end_s: float
    engagement: str  # "idle" or "active"

    @property
    def duration_s(self) -> float:
        return self.end_s - self.start_s


TIMELINE_REQUEST_INTERVAL_S = 0.1


def _alternating_timeline(*durations: float) -> List[TimelineSlice]:
    """Build alternating idle/active slices from ``durations`` pairs."""

    slices: List[TimelineSlice] = []
    cursor = 0.0
    states = ("idle", "active")
    state_idx = 0
    for duration in durations:
        start = cursor
        end = cursor + duration
        slices.append(TimelineSlice(start, end, states[state_idx % 2]))
        cursor = end
        state_idx += 1
    return slices


DUTY_CYCLE_TIMELINE: List[TimelineSlice] = _alternating_timeline(10.0, 5.0, 10.0, 5.0)
TIMELINE_DURATION_S = DUTY_CYCLE_TIMELINE[-1].end_s


def state_for_time(timestamp: float) -> str:
    """Return the engagement label for ``timestamp`` within the timeline."""

    for slice_ in DUTY_CYCLE_TIMELINE:
        if slice_.start_s <= timestamp < slice_.end_s:
            return slice_.engagement
    return DUTY_CYCLE_TIMELINE[-1].engagement


def iter_requests() -> Iterable[float]:
    """Yield request timestamps spanning the deterministic timeline."""

    t = 0.0
    while t < TIMELINE_DURATION_S:
        yield round(t, 10)
        t += TIMELINE_REQUEST_INTERVAL_S
