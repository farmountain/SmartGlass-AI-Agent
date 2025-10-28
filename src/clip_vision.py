"""
SmartGlass AI Agent - Vision Module
Uses CLIP for image understanding and vision-language tasks
"""

import torch
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import numpy as np
from typing import List, Union, Optional


class CLIPVisionProcessor:
    """
    Vision processor using OpenAI's CLIP model for image understanding.
    Enables zero-shot image classification and image-text matching.
    """
    
    def __init__(self, model_name: str = "openai/clip-vit-base-patch32", device: Optional[str] = None):
        """
        Initialize CLIP vision processor.
        
        Args:
            model_name: CLIP model name from HuggingFace
                       'openai/clip-vit-base-patch32' is recommended for smart glasses
            device: Device to run the model on ('cuda', 'cpu', or None for auto-detect)
        """
        self.device = device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Loading CLIP model '{model_name}' on device '{self.device}'...")
        
        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.model_name = model_name
        
        print(f"CLIP model loaded successfully.")
    
    def understand_image(
        self,
        image: Union[str, Image.Image, np.ndarray],
        text_queries: List[str],
        return_scores: bool = True
    ) -> dict:
        """
        Understand image content by matching it with text queries.
        
        Args:
            image: Image file path, PIL Image, or numpy array
            text_queries: List of text descriptions to match against
            return_scores: Whether to return similarity scores
        
        Returns:
            Dictionary with best match and optionally all scores
        """
        # Load image if path is provided
        if isinstance(image, str):
            image = Image.open(image)
        elif isinstance(image, np.ndarray):
            image = Image.fromarray(image)
        
        # Process inputs
        inputs = self.processor(
            text=text_queries,
            images=image,
            return_tensors="pt",
            padding=True
        ).to(self.device)
        
        # Get similarity scores
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits_per_image = outputs.logits_per_image
            probs = logits_per_image.softmax(dim=1).cpu().numpy()[0]
        
        # Find best match
        best_idx = np.argmax(probs)
        result = {
            "best_match": text_queries[best_idx],
            "confidence": float(probs[best_idx])
        }
        
        if return_scores:
            result["all_scores"] = {
                query: float(score) 
                for query, score in zip(text_queries, probs)
            }
        
        return result
    
    def classify_image(
        self,
        image: Union[str, Image.Image, np.ndarray],
        categories: List[str]
    ) -> str:
        """
        Zero-shot image classification.
        
        Args:
            image: Image file path, PIL Image, or numpy array
            categories: List of possible categories
        
        Returns:
            Best matching category
        """
        # Format categories as natural language
        text_queries = [f"a photo of a {category}" for category in categories]
        result = self.understand_image(image, text_queries, return_scores=False)
        
        # Extract category from "a photo of a {category}"
        best_match = result["best_match"]
        category = best_match.replace("a photo of a ", "")
        
        return category
    
    def get_image_features(
        self,
        image: Union[str, Image.Image, np.ndarray]
    ) -> np.ndarray:
        """
        Extract image features (embeddings) for further processing.
        
        Args:
            image: Image file path, PIL Image, or numpy array
        
        Returns:
            Image feature vector (numpy array)
        """
        # Load image if path is provided
        if isinstance(image, str):
            image = Image.open(image)
        elif isinstance(image, np.ndarray):
            image = Image.fromarray(image)
        
        # Process image
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)
        
        # Get features
        with torch.no_grad():
            image_features = self.model.get_image_features(**inputs)
        
        return image_features.cpu().numpy()[0]
    
    def describe_scene(
        self,
        image: Union[str, Image.Image, np.ndarray]
    ) -> str:
        """
        Generate a description of what's in the scene.
        
        Args:
            image: Image file path, PIL Image, or numpy array
        
        Returns:
            Scene description
        """
        # Common scene descriptions for smart glasses
        scene_types = [
            "indoor environment",
            "outdoor environment",
            "street scene",
            "nature scene",
            "office space",
            "home interior",
            "restaurant or cafe",
            "store or shopping area",
            "transportation (car, bus, train)",
            "people gathering"
        ]
        
        result = self.understand_image(image, scene_types, return_scores=True)
        
        # Get top 3 matches
        scores = result["all_scores"]
        top_matches = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
        
        description = f"Scene appears to be: {result['best_match']} "
        description += f"(confidence: {result['confidence']:.2%})"
        
        if len(top_matches) > 1:
            description += f"\nAlternatively: {top_matches[1][0]} ({top_matches[1][1]:.2%})"
        
        return description
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model."""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "capabilities": ["image classification", "scene understanding", "image-text matching"]
        }


if __name__ == "__main__":
    # Example usage
    print("CLIP Vision Processor - Example Usage")
    print("=" * 50)
    
    # Initialize processor
    vision = CLIPVisionProcessor()
    
    # Display model info
    print("\nModel Information:")
    info = vision.get_model_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    print("\nReady to process images!")
    print("\nUsage examples:")
    print("  # Classify an image")
    print("  category = vision.classify_image('image.jpg', ['cat', 'dog', 'bird'])")
    print("\n  # Understand scene with custom queries")
    print("  result = vision.understand_image('scene.jpg', ['indoor', 'outdoor'])")
    print("\n  # Describe scene")
    print("  description = vision.describe_scene('scene.jpg')")
