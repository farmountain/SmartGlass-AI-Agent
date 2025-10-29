"""Utilities for replaying gesture inputs against the SmartGlass grammar.

The runtime interface is intentionally lightweight.  The grammar is encoded as a
set of mapping tables that translate raw gesture identifiers into semantic
actions.  A small arbitration layer applies debounce rules and resolves
conflicting intents using action priorities.  The functionality is exercised in
unit tests which replay recorded gesture traces so that CI can continuously
validate behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

__all__ = [
    "DetectionBudget",
    "GestureEvent",
    "GestureGrammar",
    "GestureResolution",
    "load_detection_budgets",
]

# ---------------------------------------------------------------------------
# Mapping tables describing the gesture grammar.

#: Map low-level gesture identifiers to semantic actions.
GESTURE_TO_ACTION: Dict[str, str] = {
    "pinch": "select",
    "swipe_left": "nav_back",
    "swipe_right": "nav_forward",
    "double_tap": "confirm",
    "long_press": "open_menu",
    "shake": "dismiss",
    "circle": "emergency_stop",
}

#: Higher priority values win arbitration; a lower integer means higher priority.
ACTION_PRIORITY: Dict[str, int] = {
    "emergency_stop": 0,
    "dismiss": 1,
    "confirm": 2,
    "open_menu": 3,
    "select": 4,
    "nav_back": 5,
    "nav_forward": 6,
}

#: Per gesture debounce windows in seconds.  Events inside the window are rejected.
DEBOUNCE_WINDOWS: Dict[str, float] = {
    "pinch": 0.25,
    "swipe_left": 0.05,
    "swipe_right": 0.05,
    "double_tap": 0.30,
    "long_press": 0.80,
    "shake": 0.40,
    "circle": 1.20,
}

# ---------------------------------------------------------------------------
# Detection thresholds sourced from the UX budget configuration file.

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "ux_budgets.yaml"


@dataclass(frozen=True)
class DetectionBudget:
    """False positive / negative caps for the gesture detector."""

    false_positive_cap: float
    false_negative_cap: float


@dataclass(frozen=True)
class GestureEvent:
    """Normalised representation of a gesture input event."""

    gesture: str
    timestamp: float

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "GestureEvent":
        try:
            gesture = str(payload["gesture"]).strip()
            timestamp = float(payload["timestamp"])  # type: ignore[arg-type]
        except KeyError as exc:  # pragma: no cover - developer error path
            raise KeyError(f"Gesture event missing required key: {exc.args[0]}") from exc
        except (TypeError, ValueError) as exc:  # pragma: no cover - developer error path
            raise ValueError(f"Invalid gesture payload: {payload!r}") from exc
        return cls(gesture=gesture, timestamp=timestamp)


@dataclass(frozen=True)
class GestureResolution:
    """Result of replaying a gesture sequence through the grammar."""

    action: Optional[str]
    accepted: Tuple[GestureEvent, ...]
    rejected: Tuple[GestureEvent, ...]

    @property
    def accepted_gestures(self) -> Tuple[str, ...]:
        """Convenience accessor returning the identifiers for accepted events."""

        return tuple(event.gesture for event in self.accepted)


class GestureGrammar:
    """Apply debounce timers and priority arbitration to gesture events."""

    def __init__(
        self,
        mapping: Mapping[str, str],
        priorities: Mapping[str, int],
        debounce_windows: Mapping[str, float],
        detection_budget: DetectionBudget,
    ) -> None:
        self._mapping = dict(mapping)
        self._priorities = dict(priorities)
        self._debounce = dict(debounce_windows)
        self._detection_budget = detection_budget

    @classmethod
    def default(cls, config_path: Optional[Path] = None) -> "GestureGrammar":
        """Construct a grammar using the repository defaults."""

        budget = load_detection_budgets(config_path or DEFAULT_CONFIG_PATH)
        return cls(GESTURE_TO_ACTION, ACTION_PRIORITY, DEBOUNCE_WINDOWS, budget)

    @property
    def detection_budget(self) -> DetectionBudget:
        """Expose the detection budget used by the grammar."""

        return self._detection_budget

    def map_gesture(self, gesture: str) -> Optional[str]:
        """Return the semantic action for ``gesture`` if it exists."""

        return self._mapping.get(gesture)

    def debounce_window(self, gesture: str) -> float:
        """Return the debounce window for ``gesture`` in seconds."""

        return self._debounce.get(gesture, 0.0)

    def replay(self, events: Sequence[Mapping[str, object]]) -> GestureResolution:
        """Replay a gesture sequence and return the resolved action.

        Unknown gestures and events that arrive inside their debounce window are
        rejected.  The highest priority action amongst the accepted events wins
        arbitration.
        """

        normalised: List[Tuple[float, int, GestureEvent]] = []
        for index, payload in enumerate(events):
            event = GestureEvent.from_payload(payload)
            normalised.append((event.timestamp, index, event))
        normalised.sort()

        last_seen: MutableMapping[str, float] = {}
        accepted: List[GestureEvent] = []
        rejected: List[GestureEvent] = []
        winning_action: Optional[str] = None
        winning_priority: Optional[int] = None

        for _, _, event in normalised:
            action = self._mapping.get(event.gesture)
            if action is None:
                rejected.append(event)
                continue

            debounce = self._debounce.get(event.gesture, 0.0)
            last_timestamp = last_seen.get(event.gesture)
            if last_timestamp is not None and event.timestamp - last_timestamp < debounce:
                rejected.append(event)
                continue

            last_seen[event.gesture] = event.timestamp
            accepted.append(event)

            priority = self._priorities.get(action, float("inf"))
            if winning_action is None or priority < (winning_priority or float("inf")):
                winning_action = action
                winning_priority = priority

        return GestureResolution(
            action=winning_action,
            accepted=tuple(accepted),
            rejected=tuple(rejected),
        )


def load_detection_budgets(config_path: Path = DEFAULT_CONFIG_PATH) -> DetectionBudget:
    """Parse the gesture detection thresholds from ``ux_budgets.yaml``."""

    text = config_path.read_text(encoding="utf-8")
    in_block = False
    values: Dict[str, float] = {}

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.endswith(":"):
            in_block = stripped[:-1] == "gesture_detection"
            continue
        if not in_block or ":" not in stripped:
            continue
        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        try:
            values[key] = float(raw_value)
        except ValueError as exc:  # pragma: no cover - configuration error path
            raise ValueError(f"Invalid numeric value for {key!r}: {raw_value!r}") from exc

    expected = {"false_positive_cap", "false_negative_cap"}
    missing = expected - values.keys()
    if missing:  # pragma: no cover - configuration error path
        raise KeyError(f"Missing detection budget keys: {', '.join(sorted(missing))}")

    return DetectionBudget(
        false_positive_cap=values["false_positive_cap"],
        false_negative_cap=values["false_negative_cap"],
    )
