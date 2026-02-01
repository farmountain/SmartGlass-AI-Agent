"""
Production Planner Implementation

Rule-based planner with domain-specific planning for navigation, translation,
identification, and other common smart glass tasks.
"""

import logging
import time
from typing import Any, Dict, List, Optional

from .planner import Plan, PlanStep, Planner
from .world_model import WorldState

logger = logging.getLogger(__name__)


class RuleBasedPlanner(Planner):
    """
    Production planner using rule-based task decomposition.
    
    Features:
    - Domain-specific planning rules for common intents
    - Constraint-based plan generation (safety, max steps, timeout)
    - Confidence-weighted step selection
    - Fallback strategies for unknown intents
    """

    # Skill ID mappings for RaySkillKit
    SKILL_MAPPING = {
        "navigation": "skill_001",
        "translation": "skill_003",
        "object_recognition": "skill_004",
        "text_recognition": "skill_002",
        "notification": "skill_005",
        "reminder": "skill_006",
    }

    def __init__(
        self,
        default_max_steps: int = 5,
        default_timeout_ms: int = 5000,
        min_confidence: float = 0.3,
    ):
        """
        Initialize rule-based planner.
        
        Args:
            default_max_steps: Default maximum steps per plan
            default_timeout_ms: Default timeout for plan execution
            min_confidence: Minimum confidence for including a step
        """
        self.default_max_steps = default_max_steps
        self.default_timeout_ms = default_timeout_ms
        self.min_confidence = min_confidence

        logger.info(
            f"RuleBasedPlanner initialized: max_steps={default_max_steps}, "
            f"timeout_ms={default_timeout_ms}, min_confidence={min_confidence}"
        )

    def plan(
        self,
        user_intent: str,
        world_state: WorldState,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Optional[Plan]:
        """
        Generate execution plan from user intent and world state.
        
        Args:
            user_intent: User's intent (query or structured intent)
            world_state: Current world state
            constraints: Optional planning constraints
        
        Returns:
            Plan with ordered steps, or None if intent cannot be handled
        """
        # Parse constraints
        constraints = constraints or {}
        max_steps = constraints.get("max_steps", self.default_max_steps)
        safety_mode = constraints.get("safety_mode", True)
        timeout_ms = constraints.get("timeout_ms", self.default_timeout_ms)

        # Extract intent type from world state or parse from query
        intent_type = self._get_intent_type(user_intent, world_state)

        # Generate steps based on intent type
        steps = self._generate_steps(
            intent_type, user_intent, world_state, max_steps, safety_mode
        )

        if not steps:
            logger.debug(f"No plan generated for intent: {intent_type}")
            return None

        # Estimate total duration
        total_duration_ms = sum(step.expected_duration_ms for step in steps)

        # Check timeout constraint
        if total_duration_ms > timeout_ms:
            logger.warning(
                f"Plan exceeds timeout: {total_duration_ms}ms > {timeout_ms}ms"
            )
            # Truncate plan to fit timeout
            cumulative_duration = 0
            truncated_steps = []
            for step in steps:
                if cumulative_duration + step.expected_duration_ms <= timeout_ms:
                    truncated_steps.append(step)
                    cumulative_duration += step.expected_duration_ms
                else:
                    break
            steps = truncated_steps
            total_duration_ms = cumulative_duration

        if not steps:
            return None

        plan = Plan(
            plan_id=f"plan_{hash(user_intent) % 100000:05d}",
            intent=user_intent,
            steps=steps,
            estimated_duration_ms=total_duration_ms,
        )

        logger.info(
            f"Generated plan: {len(steps)} steps, {total_duration_ms}ms "
            f"for intent '{intent_type}'"
        )

        return plan

    def _get_intent_type(self, user_intent: str, world_state: WorldState) -> str:
        """Extract intent type from query or world state."""
        # If world state has structured intent, use it
        if world_state.intent and world_state.intent.intent_type != "unknown":
            return world_state.intent.intent_type

        # Otherwise, simple keyword matching
        user_intent_lower = user_intent.lower()

        if any(
            kw in user_intent_lower for kw in ["navigate", "direction", "how to get"]
        ):
            return "navigate"
        elif any(kw in user_intent_lower for kw in ["translate", "language", "mean"]):
            return "translate"
        elif any(kw in user_intent_lower for kw in ["what is", "identify", "recognize"]):
            return "identify"
        elif any(kw in user_intent_lower for kw in ["read", "text", "says"]):
            return "read"
        elif any(
            kw in user_intent_lower for kw in ["remind", "notification", "alert"]
        ):
            return "remind"
        else:
            return "info"  # Generic information request

    def _generate_steps(
        self,
        intent_type: str,
        user_intent: str,
        world_state: WorldState,
        max_steps: int,
        safety_mode: bool,
    ) -> List[PlanStep]:
        """Generate plan steps based on intent type."""
        steps = []

        if intent_type == "navigate":
            steps = self._plan_navigation(user_intent, world_state)
        elif intent_type == "translate":
            steps = self._plan_translation(user_intent, world_state)
        elif intent_type == "identify":
            steps = self._plan_identification(user_intent, world_state)
        elif intent_type == "read":
            steps = self._plan_text_reading(user_intent, world_state)
        elif intent_type == "remind":
            steps = self._plan_reminder(user_intent, world_state)
        elif intent_type == "info":
            steps = self._plan_information(user_intent, world_state)

        # Apply safety constraints
        if safety_mode:
            steps = self._apply_safety_filters(steps)

        # Enforce max_steps
        steps = steps[:max_steps]

        return steps

    def _plan_navigation(
        self, user_intent: str, world_state: WorldState
    ) -> List[PlanStep]:
        """Generate navigation plan."""
        steps = []

        # Step 1: Determine current location (if not known)
        if not world_state.metadata.get("location_known"):
            steps.append(
                PlanStep(
                    step_id="nav_001",
                    action_type="perception",
                    skill_id=None,
                    parameters={"mode": "location_detection"},
                    expected_duration_ms=300,
                )
            )

        # Step 2: Parse destination from query
        destination = self._extract_destination(user_intent)
        steps.append(
            PlanStep(
                step_id="nav_002",
                action_type="skill_invocation",
                skill_id=self.SKILL_MAPPING["navigation"],
                parameters={
                    "destination": destination,
                    "mode": "walking",  # Default for smart glasses
                },
                expected_duration_ms=500,
            )
        )

        # Step 3: Display directions
        steps.append(
            PlanStep(
                step_id="nav_003",
                action_type="display",
                skill_id=None,
                parameters={"content_type": "directions", "overlay": True},
                expected_duration_ms=200,
            )
        )

        return steps

    def _plan_translation(
        self, user_intent: str, world_state: WorldState
    ) -> List[PlanStep]:
        """Generate translation plan."""
        steps = []

        # Step 1: Capture/identify source text
        steps.append(
            PlanStep(
                step_id="trans_001",
                action_type="perception",
                skill_id=self.SKILL_MAPPING["text_recognition"],
                parameters={"mode": "ocr"},
                expected_duration_ms=400,
            )
        )

        # Step 2: Detect source language
        steps.append(
            PlanStep(
                step_id="trans_002",
                action_type="analysis",
                skill_id=None,
                parameters={"task": "language_detection"},
                expected_duration_ms=100,
            )
        )

        # Step 3: Translate to target language
        target_lang = self._extract_target_language(user_intent, world_state)
        steps.append(
            PlanStep(
                step_id="trans_003",
                action_type="skill_invocation",
                skill_id=self.SKILL_MAPPING["translation"],
                parameters={"target_language": target_lang},
                expected_duration_ms=300,
            )
        )

        # Step 4: Display translation
        steps.append(
            PlanStep(
                step_id="trans_004",
                action_type="display",
                skill_id=None,
                parameters={"content_type": "translation", "overlay": True},
                expected_duration_ms=200,
            )
        )

        return steps

    def _plan_identification(
        self, user_intent: str, world_state: WorldState
    ) -> List[PlanStep]:
        """Generate object identification plan."""
        steps = []

        # Step 1: Capture visual context (if not already available)
        if not world_state.objects:
            steps.append(
                PlanStep(
                    step_id="id_001",
                    action_type="perception",
                    skill_id=None,
                    parameters={"mode": "visual"},
                    expected_duration_ms=200,
                )
            )

        # Step 2: Object recognition
        steps.append(
            PlanStep(
                step_id="id_002",
                action_type="skill_invocation",
                skill_id=self.SKILL_MAPPING["object_recognition"],
                parameters={"confidence_threshold": 0.5},
                expected_duration_ms=400,
            )
        )

        # Step 3: Provide context/information about identified object
        steps.append(
            PlanStep(
                step_id="id_003",
                action_type="info_retrieval",
                skill_id=None,
                parameters={"source": "knowledge_base"},
                expected_duration_ms=300,
            )
        )

        return steps

    def _plan_text_reading(
        self, user_intent: str, world_state: WorldState
    ) -> List[PlanStep]:
        """Generate text reading plan."""
        steps = []

        # Step 1: OCR text recognition
        steps.append(
            PlanStep(
                step_id="read_001",
                action_type="perception",
                skill_id=self.SKILL_MAPPING["text_recognition"],
                parameters={"mode": "ocr"},
                expected_duration_ms=400,
            )
        )

        # Step 2: Text-to-speech output
        steps.append(
            PlanStep(
                step_id="read_002",
                action_type="output",
                skill_id=None,
                parameters={"mode": "audio", "voice": "natural"},
                expected_duration_ms=300,
            )
        )

        return steps

    def _plan_reminder(
        self, user_intent: str, world_state: WorldState
    ) -> List[PlanStep]:
        """Generate reminder/notification plan."""
        steps = []

        # Step 1: Parse reminder details (time, content)
        steps.append(
            PlanStep(
                step_id="remind_001",
                action_type="parsing",
                skill_id=None,
                parameters={"task": "extract_reminder_details"},
                expected_duration_ms=100,
            )
        )

        # Step 2: Create reminder
        steps.append(
            PlanStep(
                step_id="remind_002",
                action_type="skill_invocation",
                skill_id=self.SKILL_MAPPING["reminder"],
                parameters={"notification_type": "reminder"},
                expected_duration_ms=200,
            )
        )

        # Step 3: Confirm to user
        steps.append(
            PlanStep(
                step_id="remind_003",
                action_type="output",
                skill_id=None,
                parameters={"mode": "audio", "message": "Reminder set"},
                expected_duration_ms=100,
            )
        )

        return steps

    def _plan_information(
        self, user_intent: str, world_state: WorldState
    ) -> List[PlanStep]:
        """Generate generic information retrieval plan."""
        steps = []

        # Step 1: Query knowledge base or search
        steps.append(
            PlanStep(
                step_id="info_001",
                action_type="info_retrieval",
                skill_id=None,
                parameters={"query": user_intent, "source": "web_search"},
                expected_duration_ms=500,
            )
        )

        # Step 2: Synthesize response
        steps.append(
            PlanStep(
                step_id="info_002",
                action_type="synthesis",
                skill_id=None,
                parameters={"mode": "summarize"},
                expected_duration_ms=300,
            )
        )

        return steps

    def _apply_safety_filters(self, steps: List[PlanStep]) -> List[PlanStep]:
        """Apply safety filters to plan steps."""
        # Filter out potentially unsafe actions
        safe_steps = []
        unsafe_actions = {"system_command", "file_access", "network_write"}

        for step in steps:
            if step.action_type not in unsafe_actions:
                safe_steps.append(step)
            else:
                logger.warning(
                    f"Filtered unsafe action: {step.action_type} (step_id={step.step_id})"
                )

        return safe_steps

    def _extract_destination(self, query: str) -> str:
        """Extract destination from navigation query."""
        # Simple keyword extraction - production would use NER
        keywords = ["to", "near", "nearest", "find", "get to"]
        query_lower = query.lower()

        for kw in keywords:
            if kw in query_lower:
                parts = query_lower.split(kw, 1)
                if len(parts) > 1:
                    return parts[1].strip()

        return "unknown destination"

    def _extract_target_language(
        self, query: str, world_state: WorldState
    ) -> str:
        """Extract target language from translation query."""
        # Check world state slots first
        if world_state.intent and world_state.intent.slots.get("target_language"):
            return world_state.intent.slots["target_language"]

        # Simple keyword matching
        query_lower = query.lower()
        languages = ["english", "spanish", "french", "german", "chinese", "japanese"]

        for lang in languages:
            if lang in query_lower:
                return lang

        return "english"  # Default


if __name__ == "__main__":
    # Example usage
    from .world_model import WorldState, UserIntent

    print("Rule-Based Planner - Example Usage")
    print("=" * 60)

    # Initialize planner
    planner = RuleBasedPlanner(default_max_steps=5, min_confidence=0.3)

    print("\n✓ Planner initialized")
    print(f"  Supported skills: {list(RuleBasedPlanner.SKILL_MAPPING.keys())}")

    # Test different intent types
    print("\n" + "=" * 60)
    print("Planning Examples:")
    print("=" * 60)

    test_cases = [
        ("Navigate to the nearest coffee shop", "navigate"),
        ("Translate this sign to English", "translate"),
        ("What is this object in front of me?", "identify"),
        ("Read the text on this document", "read"),
        ("Remind me to call John at 3pm", "remind"),
    ]

    for query, expected_intent in test_cases:
        print(f"\nQuery: '{query}'")
        print(f"Expected Intent: {expected_intent}")

        # Create mock world state
        world_state = WorldState(
            timestamp_ms=int(time.time() * 1000),
            objects=[],
            intent=UserIntent(
                query=query, intent_type=expected_intent, confidence=0.8, slots={}
            ),
            metadata={},
        )

        # Generate plan
        plan = planner.plan(query, world_state)

        if plan:
            print(f"✓ Plan generated: {len(plan.steps)} steps")
            print(f"  Estimated duration: {plan.estimated_duration_ms}ms")
            for i, step in enumerate(plan.steps, 1):
                print(f"  Step {i}: {step.action_type} ({step.expected_duration_ms}ms)")
                if step.skill_id:
                    print(f"    Skill: {step.skill_id}")
        else:
            print("✗ No plan generated")

    print("\n" + "=" * 60)
    print("Ready for production use!")
