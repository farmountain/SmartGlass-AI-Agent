"""
Content Moderation Safety Layer

Implements safety guardrails to filter harmful, inappropriate, or unsafe content
before delivery to users. Critical for regulatory compliance and user safety.

PRIORITY: CRITICAL (Week 3-4 of 30-day plan)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ModerationSeverity(Enum):
    """Severity levels for content moderation flags."""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ModerationCategory(Enum):
    """Categories of harmful content to detect."""
    HATE_SPEECH = "hate_speech"
    VIOLENCE = "violence"
    SELF_HARM = "self_harm"
    SEXUAL_CONTENT = "sexual"
    MEDICAL_ADVICE = "medical_advice"
    DANGEROUS_ACTIVITY = "dangerous_activity"
    PRIVACY_VIOLATION = "privacy_violation"
    MISINFORMATION = "misinformation"


@dataclass
class ModerationResult:
    """Result of content moderation check."""
    is_safe: bool
    severity: ModerationSeverity
    categories: List[ModerationCategory]
    confidence: float
    flagged_text: Optional[str] = None
    reason: Optional[str] = None
    suggested_fallback: Optional[str] = None


class ContentModerator(ABC):
    """
    Abstract base class for content moderation services.
    
    Implementations can use:
    - OpenAI Moderation API
    - Azure Content Safety
    - Local ML models (e.g., Detoxify)
    - Rule-based filters
    """
    
    @abstractmethod
    def moderate_text(self, text: str, context: Optional[Dict[str, Any]] = None) -> ModerationResult:
        """
        Check if text content is safe for user delivery.
        
        Args:
            text: Text content to moderate
            context: Optional context (user query, action type, etc.)
            
        Returns:
            ModerationResult with safety assessment
        """
        pass
    
    @abstractmethod
    def moderate_action(self, action: Dict[str, Any]) -> ModerationResult:
        """
        Check if an action is safe to execute.
        
        Args:
            action: Action dictionary with type, payload, etc.
            
        Returns:
            ModerationResult with safety assessment
        """
        pass


class RuleBasedModerator(ContentModerator):
    """
    Simple rule-based content moderator.
    
    Uses keyword matching and heuristics. Should be replaced with ML-based
    moderation for production use.
    """
    
    # Keywords indicating harmful content (extend this list)
    HARMFUL_KEYWORDS = {
        ModerationCategory.VIOLENCE: [
            "kill", "murder", "attack", "weapon", "bomb", "shoot", "assault"
        ],
        ModerationCategory.MEDICAL_ADVICE: [
            "take this medication", "take medication", "take this pill", "take these pills",
            "diagnose", "prescribed", "cure for", "aspirin", "without prescription"
        ],
        ModerationCategory.DANGEROUS_ACTIVITY: [
            "while driving", "drunk driving", "speed limit", "run red light", 
            "drive faster", "run the red", "drive drunk"
        ],
        ModerationCategory.PRIVACY_VIOLATION: [
            "share your password", "give me your password", "tell me your ssn",
            "credit card number"
        ],
    }
    
    # Minimum confidence threshold
    CONFIDENCE_THRESHOLD = 0.5
    
    def moderate_text(self, text: str, context: Optional[Dict[str, Any]] = None) -> ModerationResult:
        """Rule-based text moderation."""
        text_lower = text.lower()
        flagged_categories = []
        max_severity = ModerationSeverity.SAFE
        
        # Check for harmful keywords
        for category, keywords in self.HARMFUL_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    flagged_categories.append(category)
                    max_severity = ModerationSeverity.HIGH
                    break
        
        # Check for medical advice combined with low confidence
        if context and context.get("confidence", 1.0) < self.CONFIDENCE_THRESHOLD:
            if any(word in text_lower for word in ["medication", "medicine", "doctor", "hospital"]):
                flagged_categories.append(ModerationCategory.MEDICAL_ADVICE)
                max_severity = ModerationSeverity.MEDIUM
        
        is_safe = max_severity in [ModerationSeverity.SAFE, ModerationSeverity.LOW]
        
        return ModerationResult(
            is_safe=is_safe,
            severity=max_severity,
            categories=flagged_categories,
            confidence=0.7,  # Rule-based has fixed confidence
            flagged_text=text if not is_safe else None,
            reason=f"Flagged categories: {[c.value for c in flagged_categories]}" if flagged_categories else None,
            suggested_fallback="I'm not able to help with that request. Please consult a professional."
            if not is_safe
            else None,
        )
    
    def moderate_action(self, action: Dict[str, Any]) -> ModerationResult:
        """Rule-based action moderation."""
        action_type = action.get("type", "")
        
        # Block navigation actions without confirmation for safety-critical scenarios
        if action_type == "navigate" or action_type == "skill_invocation":
            payload = action.get("payload", {})
            mode = payload.get("mode", "")
            
            # Flag driving navigation as potentially dangerous
            if "drive" in mode.lower():
                return ModerationResult(
                    is_safe=False,
                    severity=ModerationSeverity.HIGH,
                    categories=[ModerationCategory.DANGEROUS_ACTIVITY],
                    confidence=0.9,
                    reason="Navigation while driving requires confirmation",
                    suggested_fallback="Pull over safely before using navigation."
                )
        
        # All other actions pass by default
        return ModerationResult(
            is_safe=True,
            severity=ModerationSeverity.SAFE,
            categories=[],
            confidence=1.0
        )


class SafetyGuard:
    """
    Main safety guard that wraps content moderation.
    
    Usage in SmartGlassAgent:
        guard = SafetyGuard(moderator=RuleBasedModerator())
        
        # Before returning response
        moderation = guard.check_response(response_text, actions)
        if not moderation.is_safe:
            response_text = moderation.suggested_fallback
            actions = []  # Block unsafe actions
    """
    
    def __init__(self, moderator: Optional[ContentModerator] = None):
        """
        Initialize safety guard.
        
        Args:
            moderator: ContentModerator instance (defaults to RuleBasedModerator)
        """
        self.moderator = moderator or RuleBasedModerator()
    
    def check_response(
        self,
        response_text: str,
        actions: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> ModerationResult:
        """
        Check if response and actions are safe to deliver.
        
        Args:
            response_text: Text response to user
            actions: List of actions to execute
            context: Optional context (confidence, user query, etc.)
            
        Returns:
            ModerationResult (aggregated across text and actions)
        """
        # Moderate response text
        text_moderation = self.moderator.moderate_text(response_text, context)
        
        if not text_moderation.is_safe:
            logger.warning(
                f"Response text flagged: {text_moderation.reason}"
            )
            return text_moderation
        
        # Moderate each action
        for action in actions:
            action_moderation = self.moderator.moderate_action(action)
            if not action_moderation.is_safe:
                logger.warning(
                    f"Action flagged: {action.get('type')} - {action_moderation.reason}"
                )
                return action_moderation
        
        # All checks passed
        return ModerationResult(
            is_safe=True,
            severity=ModerationSeverity.SAFE,
            categories=[],
            confidence=1.0
        )
    
    def filter_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter out unsafe actions from list.
        
        Args:
            actions: List of actions
            
        Returns:
            Filtered list with only safe actions
        """
        safe_actions = []
        for action in actions:
            moderation = self.moderator.moderate_action(action)
            if moderation.is_safe:
                safe_actions.append(action)
            else:
                logger.warning(
                    f"Filtering unsafe action: {action.get('type')} - {moderation.reason}"
                )
        return safe_actions
