"""
Vision Processing Example

Demonstrates CLIP vision capabilities for smart glasses including:
- Scene understanding
- Object identification
- Zero-shot image classification
"""

import sys
sys.path.append('../src')

from clip_vision import CLIPVisionProcessor
from PIL import Image
import numpy as np


def create_sample_image():
    """Create a simple sample image for testing."""
    # Create a simple gradient image
    img_array = np.zeros((224, 224, 3), dtype=np.uint8)
    for i in range(224):
        img_array[i, :] = [i, i, 255 - i]
    return Image.fromarray(img_array)


def main():
    print("=" * 70)
    print("CLIP Vision Processing Example for SmartGlass")
    print("=" * 70)
    
    # Initialize vision processor
    print("\nInitializing CLIP vision processor...")
    vision = CLIPVisionProcessor()
    
    # Display model info
    print("\n" + "-" * 70)
    print("Model Information:")
    print("-" * 70)
    info = vision.get_model_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    # Create a sample image for demonstration
    print("\n" + "=" * 70)
    print("Creating sample image for demonstration...")
    print("=" * 70)
    sample_image = create_sample_image()
    print("Sample image created (224x224 gradient)")
    
    # Example 1: Scene understanding
    print("\n" + "=" * 70)
    print("Example 1: Scene Understanding")
    print("=" * 70)
    
    scene_description = vision.describe_scene(sample_image)
    print(f"\n{scene_description}")
    
    # Example 2: Zero-shot object classification
    print("\n" + "=" * 70)
    print("Example 2: Zero-Shot Object Classification")
    print("=" * 70)
    
    categories = ['abstract art', 'gradient', 'photograph', 'drawing', 'painting']
    print(f"\nCategories: {categories}")
    
    category = vision.classify_image(sample_image, categories)
    print(f"Classified as: {category}")
    
    # Example 3: Custom query matching
    print("\n" + "=" * 70)
    print("Example 3: Custom Query Matching")
    print("=" * 70)
    
    queries = [
        "a colorful abstract image",
        "a photograph of nature",
        "a digital gradient",
        "a drawing of an object"
    ]
    print(f"\nQueries: {queries}")
    
    result = vision.understand_image(sample_image, queries)
    print(f"\nBest match: {result['best_match']}")
    print(f"Confidence: {result['confidence']:.2%}")
    print("\nAll scores:")
    for query, score in result['all_scores'].items():
        print(f"  {query}: {score:.2%}")
    
    # Example 4: Image feature extraction
    print("\n" + "=" * 70)
    print("Example 4: Image Feature Extraction")
    print("=" * 70)
    
    features = vision.get_image_features(sample_image)
    print(f"\nExtracted feature vector shape: {features.shape}")
    print(f"Feature vector (first 10 values): {features[:10]}")
    
    # Real-world usage examples
    print("\n" + "=" * 70)
    print("Real-World Usage Examples for Smart Glasses")
    print("=" * 70)
    
    print("\nExample use cases:")
    print("""
    1. Identify objects in your environment:
       object = vision.classify_image(camera_frame, ['chair', 'table', 'door', 'window'])
    
    2. Navigate indoor/outdoor:
       scene = vision.describe_scene(camera_frame)
    
    3. Find specific items:
       queries = ['my keys', 'my phone', 'my wallet']
       result = vision.understand_image(camera_frame, queries)
    
    4. Accessibility - describe surroundings:
       description = vision.describe_scene(camera_frame)
       # Use text-to-speech to read description
    
    5. Shopping assistance:
       products = ['apple', 'banana', 'orange', 'milk', 'bread']
       item = vision.classify_image(camera_frame, products)
    """)
    
    print("\n" + "=" * 70)
    print("Vision processing examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
