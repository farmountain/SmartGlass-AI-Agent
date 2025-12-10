"""
Generate SNN Training Actions Script

This script uses SmartGlassAgent with SNNLLMBackend as an offline teacher to generate
training and test data for on-device SNN models. It creates synthetic multimodal scenarios
relevant to smart glasses usage and captures the agent's responses and actions.

The output JSONL file can be used to fine-tune or evaluate the on-device SNN so it learns
to emit the same structured actions as the teacher.

Usage:
    python generate_snn_training_actions.py [--output OUTPUT_FILE]

Requirements:
    - SmartGlassAgent with SNNLLMBackend configured as per API_REFERENCE.md
    - Synthetic scenario images generated inline or loaded from disk
    - Output saved in JSONL format with prompt and expected_output fields
"""

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir / "src"))
sys.path.insert(0, str(parent_dir))

from smartglass_agent import SmartGlassAgent
from llm_snn_backend import SNNLLMBackend


def create_synthetic_image(scenario_type: str) -> Image.Image:
    """
    Create a synthetic image for a given scenario type.
    
    In a production setting, you would use real images or more sophisticated
    image generation. This creates simple color-coded images to represent different scenarios.
    
    Args:
        scenario_type: Type of scenario ('road', 'supermarket', 'bus_stop', 'kitchen')
    
    Returns:
        PIL Image representing the scenario
    """
    # Create a 224x224 image with scenario-specific color patterns
    img_array = np.zeros((224, 224, 3), dtype=np.uint8)
    
    if scenario_type == "road":
        # Gray road with white lines
        img_array[:, :] = [80, 80, 80]  # Gray background
        img_array[100:124, :] = [255, 255, 255]  # White line in middle
    elif scenario_type == "supermarket":
        # Colorful shelves pattern
        for i in range(0, 224, 32):
            color = [(i * 3) % 255, (i * 5) % 255, (i * 7) % 255]
            img_array[:, i:i+16] = color
    elif scenario_type == "bus_stop":
        # Blue sky, gray shelter
        img_array[:112, :] = [135, 206, 250]  # Sky blue top half
        img_array[112:, :] = [100, 100, 100]  # Gray bottom half
    elif scenario_type == "kitchen":
        # Warm kitchen colors with counter pattern
        img_array[:, :] = [245, 222, 179]  # Beige background
        img_array[150:, :] = [139, 90, 43]  # Brown counter
    else:
        # Default: neutral gradient
        for i in range(224):
            img_array[i, :] = [i, i, 200]
    
    return Image.fromarray(img_array)


def generate_scenarios():
    """
    Define synthetic multimodal scenarios relevant to smart glasses usage.
    
    Returns:
        List of dictionaries containing scenario information:
        - name: Scenario name
        - description: Brief description
        - text_query: The user's query in this scenario
        - image: PIL Image for the scenario
    """
    scenarios = [
        {
            "name": "crossing_road",
            "description": "User is crossing a road",
            "text_query": "Is it safe to cross?",
            "image_type": "road",
        },
        {
            "name": "supermarket_aisle",
            "description": "User is in a supermarket aisle",
            "text_query": "Where can I find milk?",
            "image_type": "supermarket",
        },
        {
            "name": "bus_stop",
            "description": "User is looking at a bus stop",
            "text_query": "When is the next bus?",
            "image_type": "bus_stop",
        },
        {
            "name": "kitchen_cooking",
            "description": "User is in a kitchen cooking",
            "text_query": "What should I do next for this recipe?",
            "image_type": "kitchen",
        },
    ]
    
    # Generate synthetic images for each scenario
    for scenario in scenarios:
        scenario["image"] = create_synthetic_image(scenario["image_type"])
    
    return scenarios


def build_prompt_for_snn(text_query: str, visual_context: str) -> str:
    """
    Build the prompt that would be fed to the SNN for inference.
    
    This follows the structure that the on-device SNN will receive,
    combining the user query with visual context.
    
    Args:
        text_query: The user's text query
        visual_context: Description of the visual scene
    
    Returns:
        Formatted prompt string for the SNN
    """
    prompt = f"""You are a helpful assistant for smart glasses users. Use the provided visual context when available to deliver concise, actionable answers.

Visual context: {visual_context}
User query: {text_query}"""
    
    return prompt


def extract_expected_output(result: dict) -> dict:
    """
    Extract and structure the expected output from agent result.
    
    Args:
        result: Result dictionary from process_multimodal_query
    
    Returns:
        Structured dictionary with response and actions
    """
    return {
        "response": result.get("response", ""),
        "actions": result.get("actions", []),
    }


def main():
    """Main function to generate SNN training data."""
    print("=" * 70)
    print("SNN Training Data Generation")
    print("=" * 70)
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(
        description="Generate SNN training data from SmartGlassAgent"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="snn_training_actions.jsonl",
        help="Output JSONL file path (default: snn_training_actions.jsonl)"
    )
    args = parser.parse_args()
    
    output_file = Path(args.output)
    print(f"\nOutput file: {output_file}")
    
    # Initialize SmartGlassAgent with SNNLLMBackend
    print("\n" + "-" * 70)
    print("Initializing SmartGlassAgent with SNNLLMBackend...")
    print("-" * 70)
    
    try:
        agent = SmartGlassAgent(
            whisper_model="base",
            clip_model="openai/clip-vit-base-patch32",
            llm_backend=SNNLLMBackend(),
        )
        print("✓ Agent initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize agent: {e}")
        print("\nNote: This script requires the SmartGlassAgent and SNNLLMBackend to be properly configured.")
        print("See API_REFERENCE.md for setup instructions.")
        return 1
    
    # Generate scenarios
    print("\n" + "-" * 70)
    print("Generating synthetic scenarios...")
    print("-" * 70)
    
    scenarios = generate_scenarios()
    print(f"✓ Generated {len(scenarios)} scenarios")
    
    # Process each scenario and collect results
    print("\n" + "-" * 70)
    print("Processing scenarios with SmartGlassAgent...")
    print("-" * 70)
    
    training_data = []
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n[{i}/{len(scenarios)}] Processing: {scenario['name']}")
        print(f"  Query: {scenario['text_query']}")
        
        try:
            # Call process_multimodal_query with text and image
            result = agent.process_multimodal_query(
                text_query=scenario["text_query"],
                image_input=scenario["image"],
            )
            
            # Extract visual context and response
            visual_context = result.get("visual_context", "")
            response = result.get("response", "")
            actions = result.get("actions", [])
            
            print(f"  Visual context: {visual_context[:60]}...")
            print(f"  Response: {response[:60]}...")
            print(f"  Actions: {len(actions)} action(s) detected")
            
            # Build the prompt that will be used for SNN training
            prompt = build_prompt_for_snn(scenario["text_query"], visual_context)
            
            # Extract expected output
            expected_output = extract_expected_output(result)
            
            # Create training data entry
            training_entry = {
                "scenario_name": scenario["name"],
                "scenario_description": scenario["description"],
                "prompt": prompt,
                "expected_output": expected_output,
                "metadata": {
                    "text_query": scenario["text_query"],
                    "visual_context": visual_context,
                }
            }
            
            training_data.append(training_entry)
            print(f"  ✓ Captured training data")
            
        except Exception as e:
            print(f"  ✗ Error processing scenario: {e}")
            continue
    
    # Save results to JSONL file
    print("\n" + "-" * 70)
    print("Saving training data...")
    print("-" * 70)
    
    try:
        with output_file.open("w", encoding="utf-8") as f:
            for entry in training_data:
                f.write(json.dumps(entry) + "\n")
        
        print(f"✓ Saved {len(training_data)} entries to {output_file}")
        
        # Print statistics
        total_actions = sum(len(entry["expected_output"]["actions"]) for entry in training_data)
        print(f"\nStatistics:")
        print(f"  Total scenarios: {len(training_data)}")
        print(f"  Total actions: {total_actions}")
        print(f"  Average actions per scenario: {total_actions / len(training_data):.1f}")
        
        # Show sample entry
        if training_data:
            print(f"\nSample entry (first scenario):")
            sample = training_data[0]
            print(f"  Scenario: {sample['scenario_name']}")
            print(f"  Prompt length: {len(sample['prompt'])} characters")
            print(f"  Response length: {len(sample['expected_output']['response'])} characters")
            print(f"  Actions: {len(sample['expected_output']['actions'])}")
        
        print("\n" + "=" * 70)
        print("✓ Training data generation completed successfully!")
        print("=" * 70)
        print(f"\nNext steps:")
        print(f"1. Review the generated file: {output_file}")
        print(f"2. Use this data to fine-tune your on-device SNN model")
        print(f"3. Evaluate the SNN by comparing its outputs to expected_output")
        
        return 0
        
    except Exception as e:
        print(f"✗ Failed to save training data: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
