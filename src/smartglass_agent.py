"""
SmartGlass AI Agent - Main Agent Class
Integrates Whisper, CLIP, and GPT-2 for multimodal smart glass interactions
"""

import logging
import os
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import Image

from privacy.redact import DeterministicRedactor, RedactionSummary

from drivers.providers import BaseProvider, get_provider

from .clip_vision import CLIPVisionProcessor
from .gpt2_generator import GPT2Backend
from .llm_backend_base import BaseLLMBackend
from .whisper_processor import WhisperAudioProcessor
from .utils.metrics import record_latency


logger = logging.getLogger(__name__)


class SmartGlassAgent:
    """
    Main AI agent for smart glasses integrating audio, vision, and language capabilities.
    
    Features:
    - Speech recognition via Whisper
    - Visual understanding via CLIP
    - Natural language responses via GPT-2

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

        # Conversation history
        self.conversation_history: List[str] = []
        self.max_history = 5
    
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
    ) -> Dict[str, Any]:
        """
        Process multimodal query combining audio, vision, and text.
        
        Args:
            audio_input: Audio command (file path or array)
            image_input: Image from smart glasses
            text_query: Direct text query (if no audio)
            language: Language for audio transcription
        
        Returns:
            Dictionary containing:
                - response: Generated assistant message
                - actions: List of structured action dictionaries (empty by default)
                - raw: Nested payload preserving query, visual context, metadata, and
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

        raw_payload: Dict[str, Any] = {
            "query": query,
            "visual_context": visual_context or "No visual input",
            "metadata": metadata,
        }

        if redaction_summary is not None:
            redaction_details = redaction_summary.as_dict()
            raw_payload["redaction"] = redaction_details
            metadata["redaction_summary"] = redaction_details

        result: Dict[str, Any] = {
            "query": raw_payload["query"],
            "visual_context": raw_payload["visual_context"],
            "response": response,
            "metadata": metadata,
            "actions": [],
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
