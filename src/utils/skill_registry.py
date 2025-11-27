"""Shared helpers for loading and indexing RaySkillKit skills.

The SmartGlass agent and action builder both need awareness of which skills
exist and how their capabilities map to convenience aliases like
``navigate``/``read_sign``/``transcribe``. Centralizing the registry loading
and capability indexing keeps the mapping consistent across call sites and
allows us to validate that emitted ``skill_id`` values actually exist in the
catalog sourced from ``rayskillkit/skills.json``.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

DEFAULT_SKILLS_PATH = Path(__file__).resolve().parents[2] / "rayskillkit" / "skills.json"


def load_skill_registry(skills_path: Path | None = None) -> Dict[str, Dict[str, Any]]:
    """Load the RaySkillKit catalog and return it as a dictionary keyed by id."""

    path = skills_path or DEFAULT_SKILLS_PATH
    if not path.exists():
        logger.warning("Skill catalog not found at %s", path)
        return {}

    try:
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception:
        logger.exception("Failed to read skill catalog from %s", path)
        return {}

    skills = payload.get("skills", [])
    return {entry["id"]: entry for entry in skills if isinstance(entry, dict) and entry.get("id")}


def index_skill_capabilities(skill_registry: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
    """Map lowercased capability names and aliases to their owning skill ids."""

    capability_map: Dict[str, str] = {}
    for skill_id, entry in skill_registry.items():
        for capability in entry.get("capabilities", []):
            capability_map.setdefault(capability.lower(), skill_id)

    aliases = {
        "navigate": "navigation",
        "nav": "navigation",
        "read_sign": "vision",
        "read_signage": "vision",
        "read_signs": "vision",
        "transcribe": "speech",
        "transcription": "speech",
        "speech_to_text": "speech",
        "stt": "speech",
    }

    for alias, canonical in aliases.items():
        target_skill = capability_map.get(canonical.lower())
        if target_skill:
            capability_map.setdefault(alias.lower(), target_skill)

    return capability_map


def validate_skill_id(skill_registry: Dict[str, Dict[str, Any]], skill_id: str | None) -> bool:
    """Return ``True`` when the id exists in the loaded registry."""

    return bool(skill_id) and skill_id in skill_registry
