"""
World Model Interface

Represents the evolving state of the user's environment and intent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SceneObject:
    """A detected object in the user's environment."""

    label: str
    confidence: float
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserIntent:
    """Structured representation of inferred user intent."""

    query: str
    intent_type: str
    confidence: float
    slots: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorldState:
    """Current state snapshot derived from perception + context."""

    timestamp_ms: int
    objects: List[SceneObject] = field(default_factory=list)
    intent: Optional[UserIntent] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorldModel:
    """Base interface for maintaining world state."""

    def update(
        self,
        *,
        timestamp_ms: int,
        objects: Optional[List[SceneObject]] = None,
        intent: Optional[UserIntent] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorldState:
        raise NotImplementedError

    def current_state(self) -> WorldState:
        raise NotImplementedError
