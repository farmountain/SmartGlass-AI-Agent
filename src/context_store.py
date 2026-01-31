"""
Context Store Interface

Stores and retrieves experience frames for memory and retrieval augmentation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ExperienceFrame:
    """Normalized experience frame for memory storage."""

    frame_id: str
    session_id: str
    timestamp_ms: int
    query: str
    visual_context: str
    actions: List[Dict[str, Any]] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextQuery:
    """Query parameters for memory retrieval."""

    session_id: str
    query: str
    k: int = 8
    include_actions: bool = True
    include_raw: bool = False


@dataclass
class ContextResult:
    """Result set from a memory query."""

    session_id: str
    frames: List[ExperienceFrame]
    summary: Optional[str] = None


class ContextStore:
    """Base interface for a memory store."""

    def write(self, frame: ExperienceFrame) -> None:
        raise NotImplementedError

    def query(self, query: ContextQuery) -> ContextResult:
        raise NotImplementedError

    def session_state(self, session_id: str) -> Dict[str, Any]:
        raise NotImplementedError
