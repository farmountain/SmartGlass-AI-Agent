"""
Planner Interface

Converts inferred intent + world state into an ordered action plan.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .world_model import UserIntent, WorldState


@dataclass
class PlanStep:
    """A single planned step in an action sequence."""

    step_id: str
    action_type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    rationale: Optional[str] = None


@dataclass
class Plan:
    """Plan consisting of ordered steps."""

    plan_id: str
    steps: List[PlanStep] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class Planner:
    """Base interface for planning module."""

    def plan(
        self,
        intent: UserIntent,
        world_state: WorldState,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Plan:
        raise NotImplementedError
