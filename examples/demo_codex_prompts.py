#!/usr/bin/env python3
"""
Example script demonstrating OpenAI Codex prompts for smart glasses recommendations.

This script shows how to use the prompt template system for various recommendation
actions including Meta Ray-Ban toolkit integration, mobile companion features,
and domain-specific recommendations.
"""

import json
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def demo_meta_rayban_camera():
    """Demo: Camera frame analysis from Meta Ray-Ban glasses."""
    print("\n" + "="*60)
    print("DEMO 1: Meta Ray-Ban Camera Analysis")
    print("="*60)
    
    from src.llm_openai_codex import meta_rayban_camera_analysis
    
    result = meta_rayban_camera_analysis(
        scene_description="A busy coffee shop with people working on laptops. "
                        "Barista behind counter. Menu board visible on wall.",
        context={
            "location": "downtown coffee shop",
            "task": "find a place to sit and work",
            "timestamp": "2024-01-15 10:30:00",
        }
    )
    
    print("\nScene Description:")
    print("  'A busy coffee shop with people working on laptops...'")
    print("\nAI Analysis:")
    print(f"  {result}")


def demo_audio_command():
    """Demo: Voice command processing."""
    print("\n" + "="*60)
    print("DEMO 2: Audio Command Processing")
    print("="*60)
    
    from src.llm_openai_codex import OpenAICodexBackend
    
    backend = OpenAICodexBackend()
    
    result = backend.generate_recommendation(
        template_name="meta_rayban_audio_command.j2",
        context={
            "audio_transcript": "Navigate me to the nearest pharmacy",
            "activity": "walking",
            "location": "downtown",
            "time": "14:30",
            "available_actions": ["navigate", "search", "call", "notify"],
        },
        parse_json=False,
    )
    
    print("\nVoice Command:")
    print("  'Navigate me to the nearest pharmacy'")
    print("\nCommand Interpretation:")
    print(f"  {result}")


def demo_action_recommendation():
    """Demo: Structured action recommendation."""
    print("\n" + "="*60)
    print("DEMO 3: Structured Action Recommendation")
    print("="*60)
    
    from src.llm_openai_codex import generate_action_recommendation
    
    result = generate_action_recommendation(
        user_intent="Help me find a restaurant for dinner",
        context={
            "context": "evening, looking for dinner",
            "scene_description": "Urban street with multiple restaurants visible",
            "audio_command": "Find me a good Italian restaurant nearby",
            "available_skills": [
                "skill_001",  # Navigation
                "retail_wtp_radar",  # Price analysis
                "travel_safebubble",  # Safety assessment
            ],
        }
    )
    
    print("\nUser Intent:")
    print("  'Help me find a restaurant for dinner'")
    print("\nGenerated Action:")
    print(json.dumps(result, indent=2))


def demo_healthcare_recommendations():
    """Demo: Healthcare monitoring recommendations."""
    print("\n" + "="*60)
    print("DEMO 4: Healthcare Recommendations")
    print("="*60)
    
    from src.llm_openai_codex import healthcare_recommendation
    
    result = healthcare_recommendation(
        scenario="outdoor exercise monitoring",
        inputs={
            "visual_input": "Bright sunny day, user jogging in park, temperature 85°F",
            "audio_input": "Feeling warm and thirsty",
            "vitals": "heart_rate: 145 bpm",
            "monitoring_goals": "UV exposure and hydration safety",
        }
    )
    
    print("\nScenario:")
    print("  Outdoor exercise monitoring")
    print("\nInputs:")
    print("  - Visual: Bright sunny day, jogging in park")
    print("  - Audio: 'Feeling warm and thirsty'")
    print("  - Vitals: Heart rate 145 bpm")
    print("\nRecommendations:")
    print(json.dumps(result, indent=2))


def demo_retail_recommendations():
    """Demo: Retail shopping assistance."""
    print("\n" + "="*60)
    print("DEMO 5: Retail Shopping Recommendations")
    print("="*60)
    
    from src.llm_openai_codex import OpenAICodexBackend
    
    backend = OpenAICodexBackend()
    
    result = backend.generate_recommendation(
        template_name="retail_recommendations.j2",
        context={
            "scene_description": "Grocery store produce section with apples",
            "detected_items": [
                "Organic Honeycrisp Apples - $3.99/lb",
                "Gala Apples - $2.49/lb",
                "Fuji Apples - $2.99/lb",
            ],
            "store_type": "grocery",
            "shopping_goal": "buy apples for the week",
            "budget": "moderate",
        },
        parse_json=False,
    )
    
    print("\nShopping Context:")
    print("  - Location: Grocery store produce section")
    print("  - Goal: Buy apples for the week")
    print("  - Budget: Moderate")
    print("\nDetected Items:")
    for item in ["Organic Honeycrisp - $3.99/lb", "Gala - $2.49/lb", "Fuji - $2.99/lb"]:
        print(f"  - {item}")
    print("\nRecommendations:")
    print(f"  {result}")


def demo_travel_recommendations():
    """Demo: Travel assistance."""
    print("\n" + "="*60)
    print("DEMO 6: Travel Recommendations")
    print("="*60)
    
    from src.llm_openai_codex import OpenAICodexBackend
    
    backend = OpenAICodexBackend()
    
    result = backend.generate_recommendation(
        template_name="travel_recommendations.j2",
        context={
            "scene_description": "Airport terminal, departure gates visible",
            "user_query": "How much time do I have before boarding?",
            "location": "Terminal 2, Gate C12",
            "travel_phase": "airport",
            "destination": "San Francisco",
            "travel_mode": "flight",
        },
        parse_json=False,
    )
    
    print("\nTravel Context:")
    print("  - Location: Terminal 2, Gate C12")
    print("  - Destination: San Francisco")
    print("  - Query: 'How much time before boarding?'")
    print("\nTravel Assistance:")
    print(f"  {result}")


def demo_prompt_registry():
    """Demo: Using the prompt registry."""
    print("\n" + "="*60)
    print("DEMO 7: Prompt Registry")
    print("="*60)
    
    from src.utils.prompt_registry import (
        get_prompt_registry,
        PromptCategory,
        list_available_prompts,
    )
    
    registry = get_prompt_registry()
    
    print("\nAvailable Prompt Categories:")
    for category in registry.get_categories():
        print(f"  - {category.value}")
    
    print("\nAll Healthcare Templates:")
    healthcare_templates = registry.list_templates(PromptCategory.HEALTHCARE)
    for template in healthcare_templates:
        print(f"  - {template.name}")
        print(f"    Description: {template.description}")
        print(f"    Required: {', '.join(template.required_fields)}")
    
    print("\nSearch for 'navigation' templates:")
    nav_templates = registry.search_templates("navigation")
    for template in nav_templates:
        print(f"  - {template.name}: {template.description}")
    
    print("\nValidate context for template:")
    template_name = "meta_rayban_camera"
    test_context = {"scene_description": "test scene"}
    is_valid, missing = registry.validate_context(template_name, test_context)
    print(f"  Template: {template_name}")
    print(f"  Valid: {is_valid}")
    if missing:
        print(f"  Missing fields: {', '.join(missing)}")


def demo_snn_distillation():
    """Demo: SNN knowledge distillation configuration."""
    print("\n" + "="*60)
    print("DEMO 8: SNN Knowledge Distillation")
    print("="*60)
    
    from src.snn_knowledge_distillation import (
        SNNDistillationConfig,
        SNNDistillationTrainer,
        create_default_config,
    )
    
    # Create configuration
    config = create_default_config()
    
    print("\nDefault SNN Distillation Configuration:")
    print(f"  Teacher: {config.teacher_model}")
    print(f"  Student Architecture: {config.student_architecture}")
    print(f"  Student Size: {config.student_hidden_size}H x {config.student_num_layers}L")
    print(f"  Training: {config.num_epochs} epochs, batch size {config.batch_size}")
    print(f"  Temperature: {config.temperature}")
    print(f"  Target Latency: {config.target_latency_ms}ms")
    print(f"  Target Power: {config.target_power_mw}mW")
    print(f"  Quantization: {config.quantization_bits}-bit")
    
    # Save configuration
    output_path = "/tmp/snn_distillation_config.json"
    config.save(output_path)
    print(f"\nConfiguration saved to: {output_path}")
    
    # Initialize trainer (placeholder)
    print("\nInitializing SNN Distillation Trainer (placeholder)...")
    trainer = SNNDistillationTrainer(config)
    
    # Run placeholder training
    print("\nRunning training (placeholder)...")
    results = trainer.train()
    print(json.dumps(results, indent=2))


def demo_mobile_companion():
    """Demo: Mobile companion processing."""
    print("\n" + "="*60)
    print("DEMO 9: Mobile Companion Processing")
    print("="*60)
    
    from src.llm_openai_codex import OpenAICodexBackend
    
    backend = OpenAICodexBackend()
    
    result = backend.generate_recommendation(
        template_name="mobile_companion_processing.j2",
        context={
            "visual_input": "Restaurant menu showing pasta dishes",
            "audio_input": "Which dish would you recommend?",
            "user_name": "Alex",
            "user_preferences": {
                "dietary": "vegetarian",
                "cuisine_likes": ["Italian", "Mediterranean"],
                "budget": "moderate",
            },
            "context": "lunch at Italian restaurant",
            "recent_activity": "exploring downtown, visited 2 cafes",
        },
        parse_json=False,
    )
    
    print("\nMobile Companion Context:")
    print("  - User: Alex (vegetarian, likes Italian)")
    print("  - Visual: Restaurant menu with pasta dishes")
    print("  - Audio: 'Which dish would you recommend?'")
    print("\nCompanion Response:")
    print(f"  {result}")


def main():
    """Run all demo examples."""
    print("\n" + "="*60)
    print("OpenAI Codex Prompts for SmartGlass-AI-Agent")
    print("Demo Examples")
    print("="*60)
    
    # Note about placeholder mode
    print("\n⚠️  NOTE: Running in PLACEHOLDER mode")
    print("   Set OPENAI_API_KEY environment variable for actual responses")
    print("   Current responses are placeholders showing the system structure")
    
    try:
        # Run all demos
        demo_meta_rayban_camera()
        demo_audio_command()
        demo_action_recommendation()
        demo_healthcare_recommendations()
        demo_retail_recommendations()
        demo_travel_recommendations()
        demo_prompt_registry()
        demo_snn_distillation()
        demo_mobile_companion()
        
        print("\n" + "="*60)
        print("All demos completed successfully!")
        print("="*60)
        print("\nNext steps:")
        print("  1. Set OPENAI_API_KEY for actual AI responses")
        print("  2. Explore template files in templates/ directory")
        print("  3. Read docs/openai_codex_prompts.md for detailed documentation")
        print("  4. Use scripts/train_snn_student.py for SNN distillation")
        print("="*60)
        
    except Exception as e:
        logger.error("Demo failed: %s", e, exc_info=True)
        print("\nDemo encountered an error. See logs for details.")


if __name__ == "__main__":
    main()
