# SNN Training Data Generation

This directory contains a script to generate training data for on-device SNN (Spiking Neural Network) models using SmartGlassAgent as an offline teacher.

## Overview

The `generate_snn_training_actions.py` script:
1. Loads SmartGlassAgent with SNNLLMBackend as documented in `API_REFERENCE.md`
2. Generates synthetic multimodal scenarios relevant to smart glasses usage
3. Processes each scenario through the agent to capture responses and actions
4. Saves results to a JSONL file for training/evaluating on-device SNNs

## Scenarios

The script generates data for these scenarios:
- **Crossing a road**: Safety checks and navigation guidance
- **Supermarket aisle**: Product location and shopping assistance
- **Bus stop**: Transit information and scheduling
- **Kitchen cooking**: Recipe guidance and cooking assistance

## Usage

### Prerequisites

Install all dependencies from the repository root:

```bash
pip install -r requirements.txt
```

### Running the Script

From the `examples` directory:

```bash
# Generate training data with default output file
python generate_snn_training_actions.py

# Specify custom output file
python generate_snn_training_actions.py --output my_training_data.jsonl
```

### Testing

Validate the script structure without full dependencies:

```bash
python test_generate_snn_training_actions.py
```

This test validates:
- Image generation for all scenarios
- Prompt building format
- Output structure compatibility
- JSONL file format
- Action types match Android SDK expectations

## Output Format

Each line in the JSONL file contains:

```json
{
  "scenario_name": "crossing_road",
  "scenario_description": "User is crossing a road",
  "prompt": "System prompt + visual context + user query formatted for SNN",
  "expected_output": {
    "response": "Generated response from the teacher model",
    "actions": [
      {
        "type": "TTS_SPEAK",
        "payload": {"text": "Look both ways before crossing"}
      }
    ]
  },
  "metadata": {
    "text_query": "Is it safe to cross?",
    "visual_context": "Description of the visual scene"
  }
}
```

## Action Types

The generated actions follow the Android SDK's SmartGlassAction format:

- **SHOW_TEXT**: Display text to the user
  - Payload: `{title, body}`
- **TTS_SPEAK**: Speak text using TTS
  - Payload: `{text}`
- **NAVIGATE**: Navigate to a destination
  - Payload: `{destinationLabel?, latitude?, longitude?}`
- **REMEMBER_NOTE**: Store a note
  - Payload: `{note}`
- **OPEN_APP**: Open an Android app
  - Payload: `{packageName}`
- **SYSTEM_HINT**: Provide a system hint
  - Payload: `{hint}`

## Next Steps

After generating training data:

1. **Review the output**: Inspect the JSONL file to ensure quality
2. **Fine-tune the SNN**: Use the prompts and expected outputs for training
3. **Evaluate performance**: Compare SNN outputs against expected_output
4. **Iterate**: Generate more scenarios or adjust prompts as needed

## Implementation Notes

- **Synthetic Images**: The script generates simple synthetic images for each scenario. In production, use real images or more sophisticated generation.
- **SNNLLMBackend**: The script uses SNNLLMBackend as the teacher model. Ensure the model is properly configured.
- **Provider**: Uses the default provider (mock) for device simulation. Set `PROVIDER` environment variable to use specific hardware.

## References

- `docs/API_REFERENCE.md`: SmartGlassAgent API documentation
- `sdk-android/src/main/kotlin/com/smartglass/actions/SmartGlassAction.kt`: Android action types
- `src/llm_snn_backend.py`: SNN backend implementation
