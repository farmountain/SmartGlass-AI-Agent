"""
SmartGlass AI Agent - Main Agent Class
Integrates Whisper, CLIP, and pluggable language backends for multimodal smart
glass interactions.
"""

import json
import logging
import os
import re
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import numpy as np
from PIL import Image

from privacy.redact import DeterministicRedactor, RedactionSummary

from drivers.providers import BaseProvider, get_provider

from .clip_vision import CLIPVisionProcessor
from .gpt2_generator import GPT2Backend
from .llm_backend_base import BaseLLMBackend
from .safety import SafetyGuard, ContentModerator
from .utils.skill_registry import index_skill_capabilities, load_skill_registry, validate_skill_id
from .whisper_processor import WhisperAudioProcessor
from .utils.metrics import record_latency


logger = logging.getLogger(__name__)


class SmartGlassAgent:
    """
    Main AI agent for smart glasses integrating audio, vision, and language capabilities.
    
    Features:
    - Speech recognition via Whisper
    - Visual understanding via CLIP
    - Natural language responses via a pluggable backend

    The language model component is injected via the
    :class:`~src.llm_backend_base.BaseLLMBackend`
    protocol, enabling callers to swap in different LLM implementations
    (on-device, cloud, or mocked) without changing the agent workflow.
    """
    
    def __init__(
        self,
        whisper_model: str = "base",
        clip_model: str = "openai/clip-vit-base-patch32",
        gpt2_model: str = "gpt2",
        device: Optional[str] = None,
        redactor: Optional[
            Callable[[Union[str, Image.Image, np.ndarray]], Tuple[Any, RedactionSummary]]
        ] = None,
        llm_backend: Optional[BaseLLMBackend] = None,
        provider: Optional[Union[str, BaseProvider]] = None,
    ):
        """
        Initialize SmartGlass AI Agent.

        Args:
            whisper_model: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
            clip_model: CLIP model name from HuggingFace
            gpt2_model: Legacy GPT-2 model name retained for backwards compatibility
            device: Device to run models on ('cuda', 'cpu', or None for auto-detect)
            redactor: Optional callable used to redact imagery before cloud processing.
            llm_backend: Optional language model backend implementing
                :class:`~src.llm_backend_base.BaseLLMBackend`. When omitted, the
                legacy :class:`~src.gpt2_generator.GPT2Backend` is instantiated so
                downstream callers can inject alternative implementations (e.g.,
                cloud or distilled models) without modifying the agent logic.
            provider: Optional provider instance or name. When omitted, the
                ``PROVIDER`` environment variable (default: ``"mock"``) is read and
                :func:`drivers.providers.get_provider` is used to construct an
                instance.
        """
        print("Initializing SmartGlass AI Agent...")
        print("=" * 60)

        provider_name = os.getenv("PROVIDER", "mock")
        if provider is None:
            provider_instance = get_provider(provider_name)
            selected_provider_label = provider_name
        elif isinstance(provider, str):
            provider_instance = get_provider(provider)
            selected_provider_label = provider
        else:
            provider_instance = provider
            selected_provider_label = provider.__class__.__name__

        self.provider: BaseProvider = provider_instance
        self.camera = self.provider.open_video_stream()
        self.microphone = self.provider.open_audio_stream()

        print(f"Provider selected: {selected_provider_label}")
        logger.info("SmartGlassAgent using provider: %s", selected_provider_label)

        # Initialize components
        self.audio_processor = WhisperAudioProcessor(model_size=whisper_model, device=device)
        print("-" * 60)
        self.vision_processor = CLIPVisionProcessor(model_name=clip_model, device=device)
        print("-" * 60)
        self.llm_backend = llm_backend or GPT2Backend(model_name=gpt2_model, device=device)
        
        print("=" * 60)
        print("SmartGlass AI Agent initialized successfully!")

        # Privacy redaction pipeline
        self.redactor = redactor or DeterministicRedactor(
            mask_width=0.1,
            mask_height=0.1,
            face_padding_ratio=0.15,
            plate_padding_ratio=0.1,
            enable_face_detection=True,
            enable_plate_detection=True,
        )
        
        # Safety guardrails (CRITICAL: Week 3-4 of 30-day plan)
        self.safety_guard = SafetyGuard()
        logger.info("SafetyGuard initialized for content moderation")

        # Conversation history
        self.conversation_history: List[str] = []
        self.max_history = 5

        # RaySkillKit catalog for skill-aware actions
        self.skill_registry = load_skill_registry()
        self._capability_to_skill = index_skill_capabilities(self.skill_registry)

    # Action and skill helpers -------------------------------------------------
    def _is_valid_skill(self, skill_id: Optional[str]) -> bool:
        """Return True when the skill id exists in the loaded registry."""

        return validate_skill_id(self.skill_registry, skill_id)

    def _build_action(
        self,
        action_type: str,
        *,
        skill_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        source: str,
        result: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Normalize action dictionaries so downstream consumers can rely on a stable shape."""

        action: Dict[str, Any] = {"type": action_type}
        if skill_id:
            action["skill_id"] = skill_id
        if payload:
            action["payload"] = payload
        if result is not None:
            action["result"] = result
        action["source"] = source
        return action

    def _actions_from_json_block(self, block: str) -> List[Dict[str, Any]]:
        """Extract action candidates from JSON content embedded in model text."""

        actions: List[Dict[str, Any]] = []
        try:
            parsed = json.loads(block)
        except json.JSONDecodeError:
            return actions

        candidates = parsed if isinstance(parsed, list) else [parsed]
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            action_type = candidate.get("type") or candidate.get("action") or "skill_invocation"
            skill_id = candidate.get("skill_id") or candidate.get("skill")
            payload = candidate.get("payload")
            if payload is None:
                payload = {
                    key: value
                    for key, value in candidate.items()
                    if key not in {"type", "action", "skill", "skill_id", "result"}
                }
            if skill_id and not self._is_valid_skill(skill_id):
                logger.warning("Skipping unknown skill_id '%s' in JSON block", skill_id)
                continue
            actions.append(
                self._build_action(
                    action_type,
                    skill_id=skill_id,
                    payload=payload or None,
                    result=candidate.get("result"),
                    source="llm_json",
                )
            )
        return actions

    def _parse_actions(
        self, response_text: str, skill_signals: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Parse actions from model output and RaySkillKit runtime signals."""

        actions: List[Dict[str, Any]] = []
        linked_skills: List[Dict[str, Any]] = []
        seen_actions: Set[Tuple[str, Optional[str]]] = set()

        # Structured signals coming from RaySkillKit runtime
        if skill_signals:
            for signal in skill_signals:
                if not isinstance(signal, dict):
                    continue
                skill_id = signal.get("skill_id") or signal.get("id")
                action_type = signal.get("type") or "skill_invocation"
                payload = signal.get("payload")
                if payload is None:
                    payload = {k: v for k, v in signal.items() if k not in {"type", "skill_id", "id"}}
                if skill_id and not self._is_valid_skill(skill_id):
                    logger.warning("Dropping unknown skill_id '%s' from skill runtime signal", skill_id)
                    continue
                action = self._build_action(
                    action_type,
                    skill_id=skill_id,
                    payload=payload or None,
                    result=signal.get("result"),
                    source="skill_runtime",
                )
                key = (action_type, skill_id)
                if key not in seen_actions:
                    actions.append(action)
                    seen_actions.add(key)
                if skill_id and skill_id in self.skill_registry:
                    linked_skills.append(self.skill_registry[skill_id])

        # JSON snippets inside the LLM response
        json_blocks = re.findall(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", response_text, flags=re.DOTALL)
        for block in json_blocks:
            for action in self._actions_from_json_block(block):
                key = (action.get("type"), action.get("skill_id"))
                if key in seen_actions:
                    continue
                actions.append(action)
                seen_actions.add(key)
                skill_id = action.get("skill_id")
                if skill_id and skill_id in self.skill_registry:
                    linked_skills.append(self.skill_registry[skill_id])

        # Simple pattern matching for known skills (skill_### ids or capability hints)
        for skill_id in set(re.findall(r"skill_\d{3}", response_text)):
            if not self._is_valid_skill(skill_id):
                logger.debug("Ignoring unregistered skill id %s in response text", skill_id)
                continue
            if ("skill_invocation", skill_id) in seen_actions:
                continue
            actions.append(
                self._build_action(
                    "skill_invocation",
                    skill_id=skill_id,
                    payload={"utterance": response_text},
                    source="text_match",
                )
            )
            seen_actions.add(("skill_invocation", skill_id))
            if skill_id in self.skill_registry:
                linked_skills.append(self.skill_registry[skill_id])

        # Infer skills from capability keywords such as "navigation" or "vision"
        for capability, skill_id in self._capability_to_skill.items():
            if capability in response_text.lower():
                key = ("skill_invocation", skill_id)
                if key in seen_actions:
                    continue
                if not self._is_valid_skill(skill_id):
                    logger.debug("Ignoring capability '%s' mapped to unknown skill '%s'", capability, skill_id)
                    continue
                actions.append(
                    self._build_action(
                        "skill_invocation",
                        skill_id=skill_id,
                        payload={"capability_hint": capability, "utterance": response_text},
                        source="capability_hint",
                    )
                )
                seen_actions.add(key)
                if skill_id in self.skill_registry:
                    linked_skills.append(self.skill_registry[skill_id])

        if linked_skills:
            unique_skills = {entry["id"]: entry for entry in linked_skills if entry.get("id")}
            linked_skills = list(unique_skills.values())

        return actions, linked_skills
    
    def process_audio_command(
        self,
        audio_input: Union[str, np.ndarray],
        language: Optional[str] = None
    ) -> str:
        """
        Process audio command from user.
        
        Args:
            audio_input: Audio file path or audio array
            language: Language code (None for auto-detect)
        
        Returns:
            Transcribed text command
        """
        with record_latency("ASR"):
            if isinstance(audio_input, str):
                result = self.audio_processor.transcribe_audio(
                    audio_path=audio_input, language=language
                )
            else:
                result = self.audio_processor.transcribe_audio(
                    audio_array=audio_input, language=language
                )
        
        return result['text'].strip()
    
    def analyze_scene(
        self,
        image: Union[str, Image.Image, np.ndarray],
        custom_queries: Optional[List[str]] = None
    ) -> Dict:
        """
        Analyze scene from smart glass camera.
        
        Args:
            image: Image from smart glasses
            custom_queries: Custom queries for specific analysis
        
        Returns:
            Dictionary with scene analysis results
        """
        with record_latency("Vision"):
            if custom_queries:
                result = self.vision_processor.understand_image(image, custom_queries)
            else:
                description = self.vision_processor.describe_scene(image)
                result = {"description": description}
        
        return result
    
    def identify_object(
        self,
        image: Union[str, Image.Image, np.ndarray],
        possible_objects: List[str]
    ) -> str:
        """
        Identify object in view.
        
        Args:
            image: Image from smart glasses
            possible_objects: List of possible objects
        
        Returns:
            Identified object name
        """
        return self.vision_processor.classify_image(image, possible_objects)
    
    def generate_response(
        self,
        user_query: str,
        visual_context: Optional[str] = None
    ) -> str:
        """
        Generate natural language response to user query.
        
        Args:
            user_query: User's question or command
            visual_context: Description of what the agent sees

        Returns:
            Generated response text

        The response is produced by the configured :class:`BaseLLMBackend`, so
        alternative backends can be injected at construction time to change
        how prompts are handled (e.g., to call a cloud model instead of the
        default ANN adapter).
        """
        prompt_sections = []
        if visual_context:
            prompt_sections.append(f"Visual context: {visual_context}")
        prompt_sections.append(f"User query: {user_query}")

        prompt = "\n".join(prompt_sections)
        with record_latency("LLM"):
            response = self.llm_backend.generate(
                prompt,
                max_tokens=256,
                system_prompt=(
                    "You are a helpful assistant for smart glasses users. Use the provided "
                    "visual context when available to deliver concise, actionable answers."
                ),
            )
        
        # Update conversation history
        self.conversation_history.append(f"User: {user_query}")
        self.conversation_history.append(f"Assistant: {response}")
        
        # Keep history limited
        if len(self.conversation_history) > self.max_history * 2:
            self.conversation_history = self.conversation_history[-self.max_history * 2:]
        
        return response
    
    def process_multimodal_query(
        self,
        audio_input: Optional[Union[str, np.ndarray]] = None,
        image_input: Optional[Union[str, Image.Image, np.ndarray]] = None,
        text_query: Optional[str] = None,
        language: Optional[str] = None,
        cloud_offload: bool = False,
        skill_signals: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Process multimodal query combining audio, vision, and text.
        
        Args:
            audio_input: Audio command (file path or array)
            image_input: Image from smart glasses
            text_query: Direct text query (if no audio)
            language: Language for audio transcription
            cloud_offload: Whether to redact and offload vision processing
            skill_signals: Optional RaySkillKit runtime events that should be reflected in the returned actions
        
        Returns:
            Dictionary containing:
                - response: Generated assistant message
                - actions: List of structured action dictionaries enriched with skill IDs when available
                - raw: Nested payload preserving query, visual context, metadata, skill metadata, and
                  redaction details when available

        The prompt forwarded to the language backend combines the user query
        with any available visual context so downstream implementations can
        reason over both modalities consistently.
        """
        # Process audio if provided
        if audio_input is not None:
            query = self.process_audio_command(audio_input, language)
        elif text_query is not None:
            query = text_query
        else:
            raise ValueError("Either audio_input or text_query must be provided")
        
        # Process image if provided
        visual_context = None
        redaction_summary: Optional[RedactionSummary] = None
        metadata: Dict[str, Any] = {"cloud_offload": cloud_offload}
        if image_input is not None:
            if cloud_offload:
                redacted_image, redaction_summary = self.redactor(image_input)
                logger.info(
                    "Redaction applied before cloud processing.",
                    extra={"faces_masked": redaction_summary.faces_masked, "plates_masked": redaction_summary.plates_masked},
                )
                image_for_analysis = redacted_image
            else:
                logger.info("Processing image locally without redaction.")
                image_for_analysis = image_input

            scene_analysis = self.analyze_scene(image_for_analysis)
            visual_context = scene_analysis.get("description", "")
        
        # Generate response
        response = self.generate_response(query, visual_context)
        actions, linked_skills = self._parse_actions(response, skill_signals)
        
        # SAFETY GUARDRAIL: Check response and actions for harmful content
        # This is CRITICAL for compliance (GDPR, AI Act) and user safety
        moderation_context = {
            "query": query,
            "visual_context": visual_context,
            "confidence": metadata.get("confidence", 1.0),  # TODO: Extract from LLM backend
        }
        
        moderation_result = self.safety_guard.check_response(
            response_text=response,
            actions=actions,
            context=moderation_context
        )
        
        if not moderation_result.is_safe:
            # UNSAFE: Replace response with safe fallback
            logger.warning(
                f"Response blocked by SafetyGuard: {moderation_result.reason}",
                extra={
                    "severity": moderation_result.severity.value,
                    "categories": [c.value for c in moderation_result.categories],
                    "original_response": response[:100],  # Log truncated original
                }
            )
            response = moderation_result.suggested_fallback or "I'm not able to help with that request."
            actions = []  # Block all actions if response is unsafe
            metadata["safety_blocked"] = True
            metadata["safety_reason"] = moderation_result.reason
        else:
            # SAFE: Filter individual actions if needed (belt-and-suspenders)
            safe_actions = self.safety_guard.filter_actions(actions)
            if len(safe_actions) < len(actions):
                logger.warning(f"Filtered {len(actions) - len(safe_actions)} unsafe actions")
                actions = safe_actions
            metadata["safety_blocked"] = False

        raw_payload: Dict[str, Any] = {
            "query": query,
            "visual_context": visual_context or "No visual input",
            "metadata": metadata,
        }

        if linked_skills:
            raw_payload["skills"] = linked_skills

        if redaction_summary is not None:
            redaction_details = redaction_summary.as_dict()
            raw_payload["redaction"] = redaction_details
            metadata["redaction_summary"] = redaction_details

        result: Dict[str, Any] = {
            "query": raw_payload["query"],
            "visual_context": raw_payload["visual_context"],
            "response": response,
            "metadata": metadata,
            "actions": actions,
            "raw": raw_payload,
        }

        if redaction_summary is not None:
            result["redaction"] = redaction_details

        return result
    
    def help_identify(
        self,
        image: Union[str, Image.Image, np.ndarray],
        audio_query: Optional[Union[str, np.ndarray]] = None,
        text_query: Optional[str] = None
    ) -> str:
        """
        Help user identify what they're looking at.
        
        Args:
            image: Image from smart glasses
            audio_query: Audio question (optional)
            text_query: Text question (optional)
        
        Returns:
            Helpful identification response
        """
        # Get scene description
        scene_description = self.vision_processor.describe_scene(image)
        
        # Get user query
        if audio_query is not None:
            query = self.process_audio_command(audio_query)
        elif text_query is not None:
            query = text_query
        else:
            query = "What am I looking at?"
        
        # Generate informative response through the configured backend
        prompt_sections = [f"Scene: {scene_description}", f"Question: {query}"]
        prompt = "\n".join(prompt_sections)
        response = self.llm_backend.generate(
            prompt,
            max_tokens=128,
            system_prompt=(
                "You are a helpful assistant describing what the user is looking at. Provide "
                "concise, informative answers based on the given scene description."
            ),
        )
        
        return response
    
    def clear_conversation_history(self):
        """Clear conversation history."""
        self.conversation_history = []
    
    def get_conversation_history(self) -> List[str]:
        """Get current conversation history."""
        return self.conversation_history.copy()
    
    def get_agent_info(self) -> Dict:
        """Get information about agent components."""
        return {
            "provider": getattr(self.provider, "__class__", type(self.provider)).__name__,
            "audio": self.audio_processor.get_model_info(),
            "vision": self.vision_processor.get_model_info(),
            "language": {
                "backend": self.llm_backend.__class__.__name__,
                "model": getattr(self.llm_backend, "model_name", "unknown"),
            },
        }

    # Provider-backed ingestion helpers ---------------------------------
    def iter_camera_frames(self):
        """Stream frames from the configured provider camera."""

        return self.provider.iter_frames()

    def iter_microphone_chunks(self):
        """Stream audio chunks from the configured provider microphone."""

        return self.provider.iter_audio_chunks()


if __name__ == "__main__":
    # Example usage
    print("\n" + "=" * 60)
    print("SmartGlass AI Agent - Example Usage")
    print("=" * 60 + "\n")
    
    # Initialize agent
    agent = SmartGlassAgent(
        whisper_model="base",
        clip_model="openai/clip-vit-base-patch32",
        gpt2_model="gpt2"
    )
    
    print("\n" + "=" * 60)
    print("Agent Information:")
    print("=" * 60)
    info = agent.get_agent_info()
    for component, details in info.items():
        print(f"\n{component.upper()}:")
        for key, value in details.items():
            print(f"  {key}: {value}")
    
    print("\n" + "=" * 60)
    print("Ready to process multimodal queries!")
    print("=" * 60)
    print("\nExample usage:")
    print("  # Process multimodal query")
    print("  result = agent.process_multimodal_query(")
    print("      audio_input='command.wav',")
    print("      image_input='scene.jpg'")
    print("  )")
    print("\n  # Help identify object")
    print("  response = agent.help_identify(")
    print("      image='object.jpg',")
    print("      text_query='What is this?'")
    print("  )")
