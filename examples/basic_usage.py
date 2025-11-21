"""
Basic SmartGlass Agent Usage Example

This example demonstrates how to initialize and use the SmartGlass AI Agent
for basic multimodal interactions.
"""

import sys
sys.path.append('../src')

from smartglass_agent import SmartGlassAgent
from llm_snn_backend import SNNLLMBackend


def main():
    print("=" * 70)
    print("SmartGlass AI Agent - Basic Usage Example")
    print("=" * 70)
    
    # Initialize the agent
    print("\nInitializing SmartGlass AI Agent...")
    agent = SmartGlassAgent(
        whisper_model="base",      # Use 'tiny' for faster processing, 'base' for better accuracy
        clip_model="openai/clip-vit-base-patch32",
        gpt2_model="gpt2"
        # llm_backend defaults to ANN via GPT-2. Pass SNNLLMBackend() to experiment
        # with the placeholder SNN student implementation while keeping the same API.
    )
    
    # Display agent information
    print("\n" + "=" * 70)
    print("Agent Components Information:")
    print("=" * 70)
    info = agent.get_agent_info()
    for component, details in info.items():
        print(f"\n{component.upper()}:")
        for key, value in details.items():
            print(f"  {key}: {value}")
    
    # Example 1: Text-only query
    print("\n" + "=" * 70)
    print("Example 1: Text-Only Query")
    print("=" * 70)
    
    query = "What are smart glasses?"
    print(f"\nQuery: {query}")
    response = agent.generate_response(query)
    print(f"Response: {response}")
    
    # Example 2: Scene understanding (simulated)
    print("\n" + "=" * 70)
    print("Example 2: Scene Understanding")
    print("=" * 70)
    print("\nNote: This requires an actual image file.")
    print("Example code:")
    print("""
    # With an image file
    scene_analysis = agent.analyze_scene('path/to/image.jpg')
    print(f"Scene: {scene_analysis['description']}")
    """)
    
    # Example 3: Object identification (simulated)
    print("\n" + "=" * 70)
    print("Example 3: Object Identification")
    print("=" * 70)
    print("\nNote: This requires an actual image file.")
    print("Example code:")
    print("""
    # Identify objects in view
    possible_objects = ['car', 'bicycle', 'person', 'building', 'tree']
    object_name = agent.identify_object('path/to/image.jpg', possible_objects)
    print(f"Identified object: {object_name}")
    """)
    
    # Example 4: Multimodal query (simulated)
    print("\n" + "=" * 70)
    print("Example 4: Multimodal Query (Audio + Vision)")
    print("=" * 70)
    print("\nNote: This requires actual audio and image files.")
    print("Example code:")
    print("""
    # Process audio command with visual context
    result = agent.process_multimodal_query(
        audio_input='command.wav',
        image_input='scene.jpg'
    )
    print(f"Query: {result['query']}")
    print(f"Visual Context: {result['visual_context']}")
    print(f"Response: {result['response']}")
    """)
    
    # Example 5: Conversation history
    print("\n" + "=" * 70)
    print("Example 5: Conversation History")
    print("=" * 70)
    
    # Have a short conversation
    queries = [
        "What's the weather like?",
        "Should I bring an umbrella?",
        "What about a jacket?"
    ]
    
    print("\nHaving a conversation:")
    for q in queries:
        print(f"\nUser: {q}")
        response = agent.generate_response(q)
        print(f"Agent: {response}")
    
    # Show conversation history
    print("\n" + "-" * 70)
    print("Conversation History:")
    print("-" * 70)
    history = agent.get_conversation_history()
    for entry in history:
        print(entry)
    
    # Clear history
    agent.clear_conversation_history()
    print("\nConversation history cleared.")
    
    print("\n" + "=" * 70)
    print("Basic usage examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
