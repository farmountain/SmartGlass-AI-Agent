"""
Production World Model Implementation

CLIP-based world model that extracts scene objects, maintains spatial state,
and provides context for planning decisions.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Union

import numpy as np
from PIL import Image

from .clip_vision import CLIPVisionProcessor
from .world_model import SceneObject, UserIntent, WorldModel, WorldState

logger = logging.getLogger(__name__)


class CLIPWorldModel(WorldModel):
    """
    Production world model using CLIP for scene understanding.
    
    Extracts objects, infers spatial relationships, and maintains state history
    for context-aware planning and decision-making.
    
    Features:
    - Object detection via CLIP zero-shot classification
    - Scene type classification (indoor/outdoor, specific environments)
    - Temporal object tracking (new, persistent, disappeared)
    - Confidence scoring for all detections
    """

    # Common object categories for smart glass scenarios
    OBJECT_CATEGORIES = [
        "person",
        "face",
        "building",
        "vehicle",
        "food",
        "text",
        "sign",
        "phone",
        "computer",
        "book",
        "door",
        "stairs",
        "furniture",
        "plant",
        "animal",
        "traffic light",
        "street sign",
        "product",
        "package",
        "document",
    ]

    # Scene type categories
    SCENE_TYPES = [
        "indoor office",
        "indoor home",
        "indoor restaurant",
        "indoor store",
        "outdoor street",
        "outdoor nature",
        "outdoor parking",
        "transportation interior",
    ]

    # Intent types derived from query patterns
    INTENT_PATTERNS = {
        "identify": ["what", "identify", "recognize", "see", "looking at"],
        "navigate": ["where", "how to get", "direction", "navigate", "find"],
        "translate": ["translate", "what does", "mean", "language"],
        "read": ["read", "text", "says", "written"],
        "info": ["tell me", "information", "about", "explain"],
        "action": ["call", "message", "remind", "set", "open"],
    }

    def __init__(
        self,
        clip_processor: Optional[CLIPVisionProcessor] = None,
        confidence_threshold: float = 0.15,
        max_history: int = 10,
        device: Optional[str] = None,
    ):
        """
        Initialize CLIP world model.
        
        Args:
            clip_processor: Optional CLIP vision processor (creates one if None)
            confidence_threshold: Minimum confidence for object detection (0.0-1.0)
            max_history: Maximum number of states to keep in history
            device: Device for CLIP model ('cuda', 'cpu', or None for auto)
        """
        self.clip = clip_processor or CLIPVisionProcessor(device=device)
        self.confidence_threshold = confidence_threshold
        self.max_history = max_history

        self._current_state = WorldState(
            timestamp_ms=int(time.time() * 1000),
            objects=[],
            intent=None,
            metadata={"initialized": True},
        )
        self._state_history: List[WorldState] = [self._current_state]

        logger.info(
            f"CLIPWorldModel initialized with confidence_threshold={confidence_threshold}, "
            f"max_history={max_history}"
        )

    def update(
        self,
        *,
        timestamp_ms: int,
        objects: Optional[List[SceneObject]] = None,
        intent: Optional[UserIntent] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorldState:
        """
        Update world state with new observations.
        
        Args:
            timestamp_ms: Timestamp in milliseconds
            objects: Optional pre-detected objects (if None, uses last vision context)
            intent: Optional user intent
            metadata: Optional metadata dict
        
        Returns:
            Updated WorldState
        """
        # Create new state from current + updates
        new_objects = objects if objects is not None else self._current_state.objects
        new_intent = intent if intent is not None else self._current_state.intent
        new_metadata = {**self._current_state.metadata, **(metadata or {})}

        new_state = WorldState(
            timestamp_ms=timestamp_ms,
            objects=new_objects,
            intent=new_intent,
            metadata=new_metadata,
        )

        # Update current state
        self._current_state = new_state

        # Add to history
        self._state_history.append(new_state)
        if len(self._state_history) > self.max_history:
            self._state_history = self._state_history[-self.max_history :]

        logger.debug(
            f"World state updated: {len(new_objects)} objects, "
            f"intent={new_intent.intent_type if new_intent else 'None'}"
        )

        return new_state

    def extract_objects_from_image(
        self, image: Union[str, Image.Image, np.ndarray], top_k: int = 5
    ) -> List[SceneObject]:
        """
        Extract objects from image using CLIP zero-shot classification.
        
        Args:
            image: Image to analyze
            top_k: Number of top objects to return
        
        Returns:
            List of detected SceneObjects
        """
        # Get CLIP scores for all object categories
        result = self.clip.understand_image(
            image, self.OBJECT_CATEGORIES, return_scores=True
        )

        # Filter by confidence threshold and get top-k
        objects = []
        for label, confidence in result["all_scores"].items():
            if confidence >= self.confidence_threshold:
                objects.append(
                    SceneObject(
                        label=label,
                        confidence=float(confidence),
                        attributes={"detection_method": "clip_zero_shot"},
                    )
                )

        # Sort by confidence and take top-k
        objects.sort(key=lambda obj: obj.confidence, reverse=True)
        objects = objects[:top_k]

        logger.debug(f"Extracted {len(objects)} objects from image (top-{top_k})")

        return objects

    def classify_scene_type(
        self, image: Union[str, Image.Image, np.ndarray]
    ) -> Dict[str, float]:
        """
        Classify scene type from image.
        
        Args:
            image: Image to classify
        
        Returns:
            Dict mapping scene types to confidence scores
        """
        result = self.clip.understand_image(image, self.SCENE_TYPES, return_scores=True)
        return result["all_scores"]

    def infer_intent_from_query(
        self, query: str, confidence_threshold: float = 0.3
    ) -> UserIntent:
        """
        Infer user intent from query text using pattern matching.
        
        Args:
            query: User query text
            confidence_threshold: Minimum confidence for intent classification
        
        Returns:
            UserIntent with inferred type and confidence
        """
        query_lower = query.lower()

        # Match query against intent patterns
        intent_scores = {}
        for intent_type, patterns in self.INTENT_PATTERNS.items():
            score = sum(1 for pattern in patterns if pattern in query_lower)
            if score > 0:
                # Normalize by pattern count
                intent_scores[intent_type] = score / len(patterns)

        # Get best match
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            confidence = intent_scores[best_intent]
        else:
            best_intent = "unknown"
            confidence = 0.0

        # Extract slots (simple keyword extraction)
        slots = self._extract_slots(query_lower, best_intent)

        user_intent = UserIntent(
            query=query,
            intent_type=best_intent,
            confidence=confidence,
            slots=slots,
        )

        logger.debug(
            f"Inferred intent: {best_intent} (confidence={confidence:.2f}), slots={slots}"
        )

        return user_intent

    def _extract_slots(self, query: str, intent_type: str) -> Dict[str, Any]:
        """Extract intent slots from query (simple keyword extraction)."""
        slots = {}

        # Language detection for translation
        if intent_type == "translate":
            for lang in ["spanish", "french", "german", "chinese", "japanese"]:
                if lang in query:
                    slots["target_language"] = lang

        # Object/entity extraction for identify intent
        if intent_type == "identify":
            if "person" in query:
                slots["target_type"] = "person"
            elif "object" in query or "this" in query or "that" in query:
                slots["target_type"] = "object"

        # Direction keywords for navigation
        if intent_type == "navigate":
            if "nearest" in query:
                slots["distance_preference"] = "nearest"
            if "fastest" in query or "quickest" in query:
                slots["route_preference"] = "fastest"

        return slots

    def current_state(self) -> WorldState:
        """Get current world state."""
        return self._current_state

    def get_state_history(self, limit: Optional[int] = None) -> List[WorldState]:
        """
        Get recent state history.
        
        Args:
            limit: Optional limit on number of states to return
        
        Returns:
            List of recent WorldState objects
        """
        if limit is None:
            return self._state_history.copy()
        return self._state_history[-limit:]

    def detect_state_changes(self) -> Dict[str, Any]:
        """
        Detect significant changes between current and previous state.
        
        Returns:
            Dict with change detection results
        """
        if len(self._state_history) < 2:
            return {"has_changes": False}

        current = self._current_state
        previous = self._state_history[-2]

        # Object changes
        current_objects = {obj.label for obj in current.objects}
        previous_objects = {obj.label for obj in previous.objects}

        new_objects = current_objects - previous_objects
        disappeared_objects = previous_objects - current_objects

        # Intent changes
        intent_changed = (
            current.intent is None
            and previous.intent is not None
            or current.intent is not None
            and previous.intent is None
            or (
                current.intent
                and previous.intent
                and current.intent.intent_type != previous.intent.intent_type
            )
        )

        return {
            "has_changes": bool(new_objects or disappeared_objects or intent_changed),
            "new_objects": list(new_objects),
            "disappeared_objects": list(disappeared_objects),
            "intent_changed": intent_changed,
            "time_delta_ms": current.timestamp_ms - previous.timestamp_ms,
        }

    def update_from_vision_and_query(
        self,
        image: Union[str, Image.Image, np.ndarray],
        query: str,
        top_k_objects: int = 5,
    ) -> WorldState:
        """
        Convenience method to update state from both image and query.
        
        Args:
            image: Image to analyze
            query: User query text
            top_k_objects: Number of top objects to extract
        
        Returns:
            Updated WorldState
        """
        timestamp_ms = int(time.time() * 1000)

        # Extract objects from image
        objects = self.extract_objects_from_image(image, top_k=top_k_objects)

        # Classify scene type
        scene_types = self.classify_scene_type(image)
        best_scene = max(scene_types, key=scene_types.get)

        # Infer intent from query
        intent = self.infer_intent_from_query(query)

        # Build metadata
        metadata = {
            "scene_type": best_scene,
            "scene_confidence": scene_types[best_scene],
            "object_count": len(objects),
        }

        # Update state
        return self.update(
            timestamp_ms=timestamp_ms,
            objects=objects,
            intent=intent,
            metadata=metadata,
        )


if __name__ == "__main__":
    # Example usage
    print("CLIP World Model - Example Usage")
    print("=" * 60)

    # Initialize world model
    world_model = CLIPWorldModel(confidence_threshold=0.15)

    print("\n✓ World model initialized")
    print(f"  Object categories: {len(CLIPWorldModel.OBJECT_CATEGORIES)}")
    print(f"  Scene types: {len(CLIPWorldModel.SCENE_TYPES)}")
    print(f"  Intent patterns: {len(CLIPWorldModel.INTENT_PATTERNS)}")

    # Example: Infer intent from query
    print("\n" + "=" * 60)
    print("Intent Inference Examples:")
    print("=" * 60)

    queries = [
        "What is this object in front of me?",
        "How do I get to the nearest coffee shop?",
        "Translate this sign to English",
        "Read the text on this document",
    ]

    for query in queries:
        intent = world_model.infer_intent_from_query(query)
        print(f"\nQuery: '{query}'")
        print(f"  Intent: {intent.intent_type}")
        print(f"  Confidence: {intent.confidence:.2f}")
        print(f"  Slots: {intent.slots}")

    print("\n" + "=" * 60)
    print("Ready for image processing!")
    print("\nUsage:")
    print("  state = world_model.update_from_vision_and_query(image, query)")
    print("  objects = state.objects")
    print("  intent = state.intent")
    print("  changes = world_model.detect_state_changes()")
