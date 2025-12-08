"""Prompt Registry for OpenAI Codex Integration

This module manages the registry of available prompt templates and provides
convenient access to them for various recommendation action types.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class PromptCategory(str, Enum):
    """Categories of prompt templates."""
    
    META_RAYBAN = "meta_rayban"
    MOBILE_COMPANION = "mobile_companion"
    HEALTHCARE = "healthcare"
    RETAIL = "retail"
    TRAVEL = "travel"
    NAVIGATION = "navigation"
    TRANSLATION = "translation"
    GENERAL = "general"


@dataclass
class PromptTemplate:
    """Metadata for a prompt template."""
    
    name: str
    category: PromptCategory
    template_file: str
    description: str
    required_fields: List[str]
    optional_fields: List[str]
    output_format: str
    example_context: Optional[Dict[str, Any]] = None


class PromptRegistry:
    """
    Registry of available prompt templates for OpenAI Codex integration.
    
    This registry tracks all available prompt templates and provides methods
    to discover, validate, and access them.
    """
    
    def __init__(self, template_dir: Path = Path("templates")) -> None:
        """
        Initialize prompt registry.
        
        Args:
            template_dir: Directory containing template files
        """
        self.template_dir = template_dir
        self._templates: Dict[str, PromptTemplate] = {}
        self._register_templates()
        
        logger.info(
            "Initialized prompt registry with %d templates",
            len(self._templates)
        )
    
    def _register_templates(self) -> None:
        """Register all available prompt templates."""
        
        # Meta Ray-Ban templates
        self.register(PromptTemplate(
            name="meta_rayban_camera",
            category=PromptCategory.META_RAYBAN,
            template_file="meta_rayban_camera_analysis.j2",
            description="Analyze camera frames from Meta Ray-Ban glasses",
            required_fields=["scene_description"],
            optional_fields=["resolution", "timestamp", "location", "task"],
            output_format="text",
            example_context={
                "scene_description": "A busy street intersection with pedestrians",
                "location": "downtown",
                "task": "navigate to coffee shop",
            },
        ))
        
        self.register(PromptTemplate(
            name="meta_rayban_audio",
            category=PromptCategory.META_RAYBAN,
            template_file="meta_rayban_audio_command.j2",
            description="Process voice commands from glasses",
            required_fields=["audio_transcript"],
            optional_fields=["activity", "location", "time", "available_actions"],
            output_format="structured",
            example_context={
                "audio_transcript": "Navigate me to the nearest coffee shop",
                "activity": "walking",
                "location": "downtown",
            },
        ))
        
        self.register(PromptTemplate(
            name="meta_rayban_overlay",
            category=PromptCategory.META_RAYBAN,
            template_file="meta_rayban_overlay_display.j2",
            description="Generate overlay content for display glasses",
            required_fields=["scene_description", "current_task"],
            optional_fields=["display_mode", "user_focus"],
            output_format="structured",
        ))
        
        self.register(PromptTemplate(
            name="meta_rayban_haptic",
            category=PromptCategory.META_RAYBAN,
            template_file="meta_rayban_haptic_feedback.j2",
            description="Determine haptic feedback patterns",
            required_fields=["situation", "context"],
            optional_fields=["alert_level", "pattern_options"],
            output_format="structured",
        ))
        
        # Mobile companion templates
        self.register(PromptTemplate(
            name="mobile_companion",
            category=PromptCategory.MOBILE_COMPANION,
            template_file="mobile_companion_processing.j2",
            description="Process data from mobile companion app",
            required_fields=["visual_input", "audio_input"],
            optional_fields=["user_name", "user_preferences", "context", "recent_activity"],
            output_format="structured",
        ))
        
        self.register(PromptTemplate(
            name="contextual_recommendations",
            category=PromptCategory.GENERAL,
            template_file="contextual_recommendations.j2",
            description="Generate context-aware recommendations",
            required_fields=["scene_description", "user_query"],
            optional_fields=["location", "activity", "time_of_day", "weather", "user_state"],
            output_format="structured",
        ))
        
        # Healthcare templates
        self.register(PromptTemplate(
            name="healthcare_recommendations",
            category=PromptCategory.HEALTHCARE,
            template_file="healthcare_recommendations.j2",
            description="Healthcare monitoring and recommendations",
            required_fields=["visual_input", "audio_input"],
            optional_fields=["scenario", "monitoring_goals", "vitals"],
            output_format="structured",
        ))
        
        # Retail templates
        self.register(PromptTemplate(
            name="retail_recommendations",
            category=PromptCategory.RETAIL,
            template_file="retail_recommendations.j2",
            description="Retail shopping assistance and recommendations",
            required_fields=["scene_description", "detected_items"],
            optional_fields=["store_type", "shopping_goal", "budget"],
            output_format="structured",
        ))
        
        # Travel templates
        self.register(PromptTemplate(
            name="travel_recommendations",
            category=PromptCategory.TRAVEL,
            template_file="travel_recommendations.j2",
            description="Travel assistance and recommendations",
            required_fields=["scene_description", "user_query"],
            optional_fields=["location", "travel_phase", "destination", "travel_mode"],
            output_format="structured",
        ))
        
        # Navigation templates
        self.register(PromptTemplate(
            name="navigation_guidance",
            category=PromptCategory.NAVIGATION,
            template_file="navigation_guidance.j2",
            description="Turn-by-turn navigation guidance",
            required_fields=["current_position", "destination", "scene_description"],
            optional_fields=["nav_mode", "environment", "waypoints"],
            output_format="text",
        ))
        
        # Translation templates
        self.register(PromptTemplate(
            name="multilingual_translation",
            category=PromptCategory.TRANSLATION,
            template_file="multilingual_translation.j2",
            description="Multilingual text and speech translation",
            required_fields=["target_language"],
            optional_fields=["source_language", "context", "detected_text", "audio_input"],
            output_format="structured",
        ))
        
        # Action recommendation template
        self.register(PromptTemplate(
            name="action_recommendation",
            category=PromptCategory.GENERAL,
            template_file="action_recommendation.j2",
            description="Generate structured action recommendations",
            required_fields=["user_intent", "context"],
            optional_fields=["scene_description", "audio_command", "available_skills"],
            output_format="json",
        ))
    
    def register(self, template: PromptTemplate) -> None:
        """Register a prompt template."""
        self._templates[template.name] = template
        logger.debug("Registered template: %s", template.name)
    
    def get(self, name: str) -> Optional[PromptTemplate]:
        """Get a template by name."""
        return self._templates.get(name)
    
    def list_templates(
        self, category: Optional[PromptCategory] = None
    ) -> List[PromptTemplate]:
        """
        List all registered templates, optionally filtered by category.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of templates
        """
        if category is None:
            return list(self._templates.values())
        return [
            t for t in self._templates.values()
            if t.category == category
        ]
    
    def validate_context(
        self, template_name: str, context: Dict[str, Any]
    ) -> tuple[bool, List[str]]:
        """
        Validate that context contains required fields for a template.
        
        Args:
            template_name: Name of template
            context: Context dictionary to validate
            
        Returns:
            Tuple of (is_valid, missing_fields)
        """
        template = self.get(template_name)
        if not template:
            return False, [f"Template '{template_name}' not found"]
        
        missing = [
            field for field in template.required_fields
            if field not in context
        ]
        
        return len(missing) == 0, missing
    
    def get_categories(self) -> Set[PromptCategory]:
        """Get set of all template categories."""
        return {t.category for t in self._templates.values()}
    
    def search_templates(self, keyword: str) -> List[PromptTemplate]:
        """
        Search templates by keyword in name or description.
        
        Args:
            keyword: Search keyword
            
        Returns:
            List of matching templates
        """
        keyword_lower = keyword.lower()
        return [
            t for t in self._templates.values()
            if keyword_lower in t.name.lower() or
               keyword_lower in t.description.lower()
        ]


# Global registry instance
_global_registry: Optional[PromptRegistry] = None


def get_prompt_registry() -> PromptRegistry:
    """Get the global prompt registry instance."""
    global _global_registry
    if _global_registry is None:
        _global_registry = PromptRegistry()
    return _global_registry


def list_available_prompts(category: Optional[str] = None) -> List[str]:
    """
    List names of all available prompts.
    
    Args:
        category: Optional category filter
        
    Returns:
        List of template names
    """
    registry = get_prompt_registry()
    cat = PromptCategory(category) if category else None
    templates = registry.list_templates(cat)
    return [t.name for t in templates]


__all__ = [
    "PromptCategory",
    "PromptTemplate",
    "PromptRegistry",
    "get_prompt_registry",
    "list_available_prompts",
]
