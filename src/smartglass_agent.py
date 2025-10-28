"""
SmartGlass AI Agent - Main Agent Class
Integrates Whisper, CLIP, and GPT-2 for multimodal smart glass interactions
"""

import numpy as np
from typing import Optional, Union, List, Dict
from PIL import Image

from .whisper_processor import WhisperAudioProcessor
from .clip_vision import CLIPVisionProcessor
from .gpt2_generator import GPT2TextGenerator


class SmartGlassAgent:
    """
    Main AI agent for smart glasses integrating audio, vision, and language capabilities.
    
    Features:
    - Speech recognition via Whisper
    - Visual understanding via CLIP
    - Natural language responses via GPT-2
    """
    
    def __init__(
        self,
        whisper_model: str = "base",
        clip_model: str = "openai/clip-vit-base-patch32",
        gpt2_model: str = "gpt2",
        device: Optional[str] = None
    ):
        """
        Initialize SmartGlass AI Agent.
        
        Args:
            whisper_model: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
            clip_model: CLIP model name from HuggingFace
            gpt2_model: GPT-2 model name ('gpt2', 'gpt2-medium', 'gpt2-large', 'gpt2-xl')
            device: Device to run models on ('cuda', 'cpu', or None for auto-detect)
        """
        print("Initializing SmartGlass AI Agent...")
        print("=" * 60)
        
        # Initialize components
        self.audio_processor = WhisperAudioProcessor(model_size=whisper_model, device=device)
        print("-" * 60)
        self.vision_processor = CLIPVisionProcessor(model_name=clip_model, device=device)
        print("-" * 60)
        self.text_generator = GPT2TextGenerator(model_name=gpt2_model, device=device)
        
        print("=" * 60)
        print("SmartGlass AI Agent initialized successfully!")
        
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
        if isinstance(audio_input, str):
            result = self.audio_processor.transcribe_audio(audio_path=audio_input, language=language)
        else:
            result = self.audio_processor.transcribe_audio(audio_array=audio_input, language=language)
        
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
        """
        response = self.text_generator.generate_smart_response(
            user_query,
            context=visual_context,
            response_type="helpful"
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
        language: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Process multimodal query combining audio, vision, and text.
        
        Args:
            audio_input: Audio command (file path or array)
            image_input: Image from smart glasses
            text_query: Direct text query (if no audio)
            language: Language for audio transcription
        
        Returns:
            Dictionary with query, context, and response
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
        if image_input is not None:
            scene_analysis = self.analyze_scene(image_input)
            visual_context = scene_analysis.get("description", "")
        
        # Generate response
        response = self.generate_response(query, visual_context)
        
        return {
            "query": query,
            "visual_context": visual_context or "No visual input",
            "response": response
        }
    
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
        
        # Generate informative response
        response = self.text_generator.generate_smart_response(
            query,
            context=scene_description,
            response_type="informative"
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
            "audio": self.audio_processor.get_model_info(),
            "vision": self.vision_processor.get_model_info(),
            "language": self.text_generator.get_model_info()
        }


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
