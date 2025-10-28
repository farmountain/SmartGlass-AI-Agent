"""
SmartGlass AI Agent - Audio Processing Module
Uses OpenAI Whisper for speech-to-text transcription
"""

import whisper
import torch
import numpy as np
from typing import Optional, Union
import soundfile as sf


class WhisperAudioProcessor:
    """
    Audio processor using OpenAI's Whisper model for speech recognition.
    Optimized for real-time processing on smart glasses.
    """
    
    def __init__(self, model_size: str = "base", device: Optional[str] = None):
        """
        Initialize Whisper audio processor.
        
        Args:
            model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
                       'base' is recommended for smart glasses (balance of speed and accuracy)
            device: Device to run the model on ('cuda', 'cpu', or None for auto-detect)
        """
        self.device = device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Loading Whisper model '{model_size}' on device '{self.device}'...")
        self.model = whisper.load_model(model_size, device=self.device)
        self.model_size = model_size
        print(f"Whisper model loaded successfully.")
    
    def transcribe_audio(
        self, 
        audio_path: Optional[str] = None,
        audio_array: Optional[np.ndarray] = None,
        language: Optional[str] = None,
        task: str = "transcribe"
    ) -> dict:
        """
        Transcribe audio file or array to text.
        
        Args:
            audio_path: Path to audio file (wav, mp3, etc.)
            audio_array: NumPy array containing audio data (16kHz)
            language: Language code (e.g., 'en', 'es'). None for auto-detect
            task: 'transcribe' or 'translate' (translate to English)
        
        Returns:
            Dictionary containing 'text' and other transcription details
        """
        if audio_path is None and audio_array is None:
            raise ValueError("Either audio_path or audio_array must be provided")
        
        # Use audio array if provided, otherwise load from path
        if audio_array is not None:
            audio = audio_array
        else:
            audio, sr = sf.read(audio_path)
            # Convert to mono if stereo
            if len(audio.shape) > 1:
                audio = audio.mean(axis=1)
        
        # Whisper expects float32 audio
        audio = audio.astype(np.float32)
        
        # Transcribe
        result = self.model.transcribe(
            audio,
            language=language,
            task=task,
            fp16=(self.device == "cuda")
        )
        
        return result
    
    def transcribe_realtime(self, audio_chunk: np.ndarray) -> str:
        """
        Transcribe audio chunk for real-time processing.
        
        Args:
            audio_chunk: Audio data chunk (16kHz sample rate)
        
        Returns:
            Transcribed text
        """
        result = self.transcribe_audio(audio_array=audio_chunk)
        return result['text'].strip()
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model."""
        return {
            "model_size": self.model_size,
            "device": self.device,
            "language_support": "multilingual" if self.model_size != "tiny.en" else "English only"
        }


if __name__ == "__main__":
    # Example usage
    print("Whisper Audio Processor - Example Usage")
    print("=" * 50)
    
    # Initialize processor
    processor = WhisperAudioProcessor(model_size="base")
    
    # Display model info
    print("\nModel Information:")
    info = processor.get_model_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    print("\nReady to process audio!")
    print("\nUsage example:")
    print("  result = processor.transcribe_audio('audio.wav')")
    print("  text = result['text']")
