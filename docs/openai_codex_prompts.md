# OpenAI Codex Prompts for SmartGlass-AI-Agent

This document describes the OpenAI Codex prompt system integrated into SmartGlass-AI-Agent for generating intelligent recommendations and actions for smart glasses users.

## Overview

The OpenAI Codex integration provides a sophisticated prompt-based system for:

- **Meta Ray-Ban Wearable Access**: Camera analysis, audio processing, overlay generation, haptic feedback
- **Mobile Companion Features**: Multi-device coordination, context-aware notifications, user preference learning
- **Domain-Specific Recommendations**: Healthcare, retail, travel, navigation
- **Structured Action Generation**: JSON-formatted actions compatible with RaySkillKit

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  User Input (Voice/Vision/Context)                          │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│  Prompt Template Selection                                  │
│  - Match input to appropriate template                      │
│  - Gather contextual variables                              │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│  Jinja2 Template Rendering                                  │
│  - Inject context into prompt template                      │
│  - Generate structured prompt for OpenAI                    │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│  OpenAI Codex Backend                                       │
│  - GPT-3.5-turbo / GPT-4                                   │
│  - Temperature, max_tokens configuration                    │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│  Response Processing                                        │
│  - Parse JSON if structured output                          │
│  - Validate action schema                                   │
│  - Map to RaySkillKit skills                                │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│  Action Execution                                           │
│  - Invoke appropriate skill                                 │
│  - Generate user feedback                                   │
│  - Update conversation context                              │
└─────────────────────────────────────────────────────────────┘
```

## Template Categories

### 1. Meta Ray-Ban Wearable Access Toolkit

#### Camera Analysis (`meta_rayban_camera_analysis.j2`)

Analyzes camera frames from Ray-Ban Meta glasses.

**Required Context:**
- `scene_description`: Description of visual scene

**Optional Context:**
- `resolution`: Camera resolution (default: "720x960")
- `timestamp`: Frame timestamp
- `location`: User location
- `task`: Current user task

**Output Format:** Text response optimized for audio feedback

**Example Usage:**
```python
from src.llm_openai_codex import meta_rayban_camera_analysis

result = meta_rayban_camera_analysis(
    scene_description="A busy intersection with traffic lights",
    context={
        "location": "downtown",
        "task": "navigate to office"
    }
)
print(result)
# Output: "Traffic light shows red. Three pedestrians crossing from left. 
#          Safe to wait. Office building visible ahead on right side."
```

#### Audio Command Processing (`meta_rayban_audio_command.j2`)

Processes voice commands from glasses microphone.

**Required Context:**
- `audio_transcript`: Transcribed voice command

**Optional Context:**
- `activity`: Current activity (walking, driving, etc.)
- `location`: User location
- `time`: Current time
- `available_actions`: List of available actions

**Output Format:** Structured command interpretation

**Example Usage:**
```python
from src.llm_openai_codex import OpenAICodexBackend

backend = OpenAICodexBackend()
result = backend.generate_recommendation(
    template_name="meta_rayban_audio_command.j2",
    context={
        "audio_transcript": "Find the nearest coffee shop",
        "activity": "walking",
        "location": "downtown"
    },
    parse_json=False
)
```

#### Overlay Display (`meta_rayban_overlay_display.j2`)

Generates content for display glasses overlay.

**Required Context:**
- `scene_description`: Current visual scene
- `current_task`: Active user task

**Optional Context:**
- `display_mode`: Overlay mode (ambient, focused, navigation)
- `user_focus`: Where user is looking

**Output Format:** Structured overlay specification

**Example:**
```python
context = {
    "scene_description": "Street with restaurant ahead",
    "current_task": "find lunch location",
    "display_mode": "navigation"
}
```

#### Haptic Feedback (`meta_rayban_haptic_feedback.j2`)

Determines appropriate haptic patterns for notifications.

**Required Context:**
- `situation`: Current situation requiring haptic feedback
- `context`: Additional context

**Optional Context:**
- `alert_level`: Urgency level (normal, caution, urgent)
- `pattern_options`: Available haptic patterns

### 2. Mobile Companion Features

#### Mobile Companion Processing (`mobile_companion_processing.j2`)

Coordinates between glasses and mobile companion app.

**Required Context:**
- `visual_input`: Visual data from glasses
- `audio_input`: Audio data from glasses

**Optional Context:**
- `user_name`: User name for personalization
- `user_preferences`: User preference dictionary
- `context`: Current context
- `recent_activity`: Recent user activities

**Example:**
```python
context = {
    "visual_input": "Restaurant menu",
    "audio_input": "What's the best value here?",
    "user_preferences": {
        "dietary": "vegetarian",
        "budget": "moderate"
    },
    "context": "lunchtime at Italian restaurant"
}
```

### 3. Domain-Specific Recommendations

#### Healthcare Recommendations (`healthcare_recommendations.j2`)

Generates health monitoring recommendations.

**Required Context:**
- `visual_input`: Visual observations
- `audio_input`: Voice input

**Optional Context:**
- `scenario`: Healthcare scenario
- `monitoring_goals`: Monitoring objectives
- `vitals`: Vital signs data

**Privacy:** All data marked as PHI_SYNTHETIC (synthetic for testing)

**Available Skills:**
- `hc_gait_guard`: Gait stability monitoring
- `hc_med_sentinel`: Medication adherence
- `hc_sun_hydro`: UV/hydration coaching

**Example:**
```python
from src.llm_openai_codex import healthcare_recommendation

result = healthcare_recommendation(
    scenario="outdoor activity monitoring",
    inputs={
        "visual_input": "Bright sunny day, user walking in park",
        "audio_input": "Feeling a bit tired",
        "monitoring_goals": "UV exposure and hydration"
    }
)
```

#### Retail Recommendations (`retail_recommendations.j2`)

Shopping assistance and product recommendations.

**Required Context:**
- `scene_description`: Store/product scene
- `detected_items`: Items detected in scene

**Optional Context:**
- `store_type`: Type of store
- `shopping_goal`: Shopping objective
- `budget`: Budget constraints

**Available Skills:**
- `retail_wtp_radar`: Willingness-to-pay estimation
- `retail_capsule_gaps`: Inventory forecasting
- `retail_minute_meal`: Quick-service timing

#### Travel Recommendations (`travel_recommendations.j2`)

Travel assistance and navigation.

**Required Context:**
- `scene_description`: Current scene
- `user_query`: User question/request

**Optional Context:**
- `location`: Current location
- `travel_phase`: Phase of travel (airport, flight, destination)
- `destination`: Final destination
- `travel_mode`: Mode of transport

**Available Skills:**
- `travel_fastlane`: Airport wait time estimation
- `travel_safebubble`: Safety risk assessment
- `travel_bargaincoach`: Fare forecasting

### 4. Navigation and Translation

#### Navigation Guidance (`navigation_guidance.j2`)

Turn-by-turn navigation instructions.

**Required Context:**
- `current_position`: Current location
- `destination`: Target destination
- `scene_description`: Visual scene

**Optional Context:**
- `nav_mode`: Navigation mode (walking, driving, transit)
- `environment`: Indoor or outdoor
- `waypoints`: Intermediate waypoints

#### Multilingual Translation (`multilingual_translation.j2`)

Real-time translation of text and speech.

**Required Context:**
- `target_language`: Language to translate to

**Optional Context:**
- `source_language`: Source language (auto-detect if not provided)
- `context`: Context of translation
- `detected_text`: Text from vision
- `audio_input`: Audio to translate

## Action Recommendation System

The `action_recommendation.j2` template generates structured action recommendations compatible with RaySkillKit.

**Output Schema:**
```json
{
  "primary_action": {
    "type": "skill_invocation",
    "skill_id": "skill_001",
    "confidence": 0.95,
    "payload": {
      "destination": "Coffee Shop",
      "mode": "navigate"
    }
  },
  "explanation": "Navigating to nearest coffee shop",
  "alternatives": [
    {
      "type": "skill_invocation",
      "skill_id": "skill_002",
      "payload": { "query": "coffee shops nearby" }
    }
  ],
  "safety_check": "No hazards detected",
  "estimated_duration": "120 seconds"
}
```

**Example Usage:**
```python
from src.llm_openai_codex import generate_action_recommendation

result = generate_action_recommendation(
    user_intent="Find nearby coffee",
    context={
        "scene_description": "Street corner downtown",
        "audio_command": "Show me coffee shops",
        "available_skills": ["skill_001", "skill_002", "skill_003"]
    }
)

# Execute primary action
if "primary_action" in result:
    action = result["primary_action"]
    skill_id = action["skill_id"]
    payload = action["payload"]
    # Invoke RaySkillKit skill...
```

## Setup and Configuration

### 1. Install Dependencies

```bash
pip install openai jinja2
```

### 2. Configure API Key

```bash
export OPENAI_API_KEY="your-api-key-here"
```

### 3. Initialize Backend

```python
from src.llm_openai_codex import OpenAICodexBackend

# Initialize with defaults
backend = OpenAICodexBackend()

# Or customize
backend = OpenAICodexBackend(
    model="gpt-4",
    temperature=0.7,
    max_tokens=512,
    template_dir="templates"
)
```

### 4. Use with SmartGlassAgent

```python
from src.smartglass_agent import SmartGlassAgent
from src.llm_openai_codex import OpenAICodexBackend

# Create backend
codex_backend = OpenAICodexBackend(model="gpt-3.5-turbo")

# Initialize agent with Codex backend
agent = SmartGlassAgent(
    whisper_model="base",
    clip_model="openai/clip-vit-base-patch32",
    llm_backend=codex_backend,
    provider="meta"
)

# Process multimodal query
result = agent.process_multimodal_query(
    text_query="What should I do here?",
    image_input="path/to/image.jpg"
)
```

## Prompt Registry

The `PromptRegistry` class provides centralized management of all prompt templates.

```python
from src.utils.prompt_registry import get_prompt_registry, PromptCategory

# Get registry
registry = get_prompt_registry()

# List all templates
all_templates = registry.list_templates()

# List by category
healthcare_templates = registry.list_templates(PromptCategory.HEALTHCARE)

# Get specific template
template = registry.get("meta_rayban_camera")
print(f"Required fields: {template.required_fields}")
print(f"Optional fields: {template.optional_fields}")

# Validate context
is_valid, missing = registry.validate_context(
    "meta_rayban_camera",
    {"scene_description": "A street"}
)
if not is_valid:
    print(f"Missing fields: {missing}")

# Search templates
nav_templates = registry.search_templates("navigation")
```

## Best Practices

### 1. Context Management

- Always provide required fields
- Include as much optional context as available
- Use meaningful descriptions in `scene_description`
- Keep audio transcripts clean and accurate

### 2. Error Handling

```python
try:
    result = backend.generate_recommendation(
        template_name="meta_rayban_camera",
        context=context,
        parse_json=True
    )
    if "error" in result:
        # Handle error
        logger.error("Generation failed: %s", result["error"])
except Exception as e:
    logger.error("Failed to generate recommendation: %s", e)
    # Fallback to default behavior
```

### 3. Response Validation

```python
from src.utils.action_builder import ActionBuilder

# Validate generated actions
action_builder = ActionBuilder()
for action in result.get("actions", []):
    skill_id = action.get("skill_id")
    if not action_builder.is_valid_skill(skill_id):
        logger.warning("Invalid skill_id: %s", skill_id)
```

### 4. Rate Limiting

```python
import time

def generate_with_retry(backend, template, context, max_retries=3):
    for attempt in range(max_retries):
        try:
            return backend.generate_recommendation(
                template_name=template,
                context=context
            )
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            raise
```

## Testing

Example test for prompt generation:

```python
def test_meta_rayban_camera_prompt():
    from src.llm_openai_codex import OpenAICodexBackend
    
    backend = OpenAICodexBackend()
    context = {
        "scene_description": "Test scene",
        "location": "test location"
    }
    
    result = backend.generate_recommendation(
        template_name="meta_rayban_camera_analysis.j2",
        context=context,
        parse_json=False
    )
    
    assert isinstance(result, str)
    assert len(result) > 0
```

## Placeholder Note

⚠️ **Important:** The OpenAI Codex integration is currently a **placeholder implementation**. To enable full functionality:

1. Install the OpenAI Python package: `pip install openai`
2. Set your API key: `export OPENAI_API_KEY="your-key"`
3. Uncomment the client initialization code in `src/llm_openai_codex.py`

In stub mode (without API key), the backend will return placeholder responses for testing the prompt template system.

## Future Enhancements

- [ ] Add streaming response support
- [ ] Implement conversation history management
- [ ] Add prompt optimization based on user feedback
- [ ] Create domain-specific fine-tuned models
- [ ] Add A/B testing framework for prompts
- [ ] Implement prompt versioning and rollback
- [ ] Add metrics and monitoring for prompt performance

## Related Documentation

- [Meta DAT Integration Guide](meta_dat_integration.md)
- [Actions and Skills](actions_and_skills.md)
- [SNN Pipeline](snn_pipeline.md)
- [Hello SmartGlass Quickstart](hello_smartglass_quickstart.md)

## Support

For questions or issues with the OpenAI Codex integration, please refer to:
- GitHub Issues: https://github.com/farmountain/SmartGlass-AI-Agent/issues
- Main README: [README.md](../README.md)
