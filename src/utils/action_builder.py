"""Action suggestion builder powered by the RaySkillKit registry.

The builder consumes ``rayskillkit/skills.json`` to align capability hints
with concrete ``skill_id`` values. Suggested actions are normalized to a
consistent shape and include lightweight payload scaffolding so downstream
callers know which fields to populate.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

try:  # pragma: no cover - support direct module loading without package context
    from .skill_registry import index_skill_capabilities, load_skill_registry, validate_skill_id
except ImportError:  # pragma: no cover - fallback when relative import is unavailable
    import importlib.util

    _SKILL_REGISTRY_PATH = Path(__file__).resolve().parent / "skill_registry.py"
    spec = importlib.util.spec_from_file_location("skill_registry", _SKILL_REGISTRY_PATH)
    if not spec or not spec.loader:
        raise
    _skill_registry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_skill_registry)
    index_skill_capabilities = _skill_registry.index_skill_capabilities
    load_skill_registry = _skill_registry.load_skill_registry
    validate_skill_id = _skill_registry.validate_skill_id

logger = logging.getLogger(__name__)

_PAYLOAD_SCAFFOLD = {
    "skill_001": {"destination": None, "waypoints": [], "mode": "navigate"},
    "skill_002": {"image": None, "query": "read_signage"},
    "skill_003": {"audio": None, "language": None},
}


class ActionBuilder:
    """Build structured action suggestions from capability hints or skill ids."""

    def __init__(self) -> None:
        self.skill_registry = load_skill_registry()
        self.capability_to_skill = index_skill_capabilities(self.skill_registry)

    def _payload_for(self, skill_id: str, capability_hint: str | None = None) -> Dict[str, Any]:
        payload = dict(_PAYLOAD_SCAFFOLD.get(skill_id, {}))
        if capability_hint:
            payload.setdefault("capability_hint", capability_hint)
        return payload

    def _build_action(
        self, action_type: str, *, skill_id: str, capability_hint: str | None = None
    ) -> Dict[str, Any]:
        action: Dict[str, Any] = {"type": action_type, "skill_id": skill_id}
        payload = self._payload_for(skill_id, capability_hint)
        if payload:
            action["payload"] = payload
        return action

    def is_valid_skill(self, skill_id: str | None) -> bool:
        """Expose registry validation so callers can gate unknown skills."""

        return validate_skill_id(self.skill_registry, skill_id)

    def suggest_actions(
        self,
        *,
        capabilities: Sequence[str] | None = None,
        skills: Sequence[str] | None = None,
        action_type: str = "skill_invocation",
    ) -> List[Dict[str, Any]]:
        """Return normalized actions for known capabilities or skill ids."""

        suggestions: List[Dict[str, Any]] = []
        seen: set[Tuple[str, str]] = set()

        for capability in capabilities or []:
            skill_id = self.capability_to_skill.get(capability.lower())
            if not self.is_valid_skill(skill_id):
                logger.warning("Ignoring unknown skill for capability '%s'", capability)
                continue

            key = (action_type, skill_id)
            if key in seen:
                continue

            suggestions.append(
                self._build_action(action_type, skill_id=skill_id, capability_hint=capability)
            )
            seen.add(key)

        for skill_id in skills or []:
            if not self.is_valid_skill(skill_id):
                logger.warning("Dropping requested unknown skill_id '%s'", skill_id)
                continue

            key = (action_type, skill_id)
            if key in seen:
                continue

            suggestions.append(self._build_action(action_type, skill_id=skill_id))
            seen.add(key)

        return suggestions
