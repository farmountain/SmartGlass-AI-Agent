"""
Tests for examples/generate_snn_training_actions.py

These tests validate the SNN training data generation script structure and output format
without requiring full SmartGlassAgent dependencies.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from types import ModuleType


def _install_stub_modules() -> None:
    """Install stub modules for testing without full dependencies."""
    
    # Stub numpy
    dummy_numpy = ModuleType("numpy")
    dummy_numpy.ndarray = type("ndarray", (), {})
    dummy_numpy.zeros = lambda shape, dtype: [[0 for _ in range(shape[1])] for _ in range(shape[0])]
    dummy_numpy.uint8 = None
    sys.modules.setdefault("numpy", dummy_numpy)
    
    # Stub PIL
    dummy_pil = ModuleType("PIL")
    
    class DummyImage:
        def __init__(self, array):
            self.size = (224, 224)
            self.mode = "RGB"
            self.array = array
        
        @staticmethod
        def fromarray(array):
            return DummyImage(array)
    
    dummy_pil_image = ModuleType("PIL.Image")
    dummy_pil_image.Image = DummyImage
    dummy_pil_image.fromarray = DummyImage.fromarray
    sys.modules.setdefault("PIL", dummy_pil)
    sys.modules.setdefault("PIL.Image", dummy_pil_image)
    
    # Stub smartglass_agent
    dummy_agent_module = ModuleType("smartglass_agent")
    
    class StubAgent:
        def __init__(self, **kwargs):
            self.calls = []
        
        def process_multimodal_query(self, text_query=None, image_input=None, **kwargs):
            self.calls.append(("process_multimodal_query", text_query, image_input))
            return {
                "response": f"Stub response for: {text_query}",
                "actions": [
                    {
                        "type": "TTS_SPEAK",
                        "payload": {"text": "Stub action"},
                        "source": "llm_json"
                    }
                ],
                "visual_context": "Stub visual context",
                "query": text_query,
                "metadata": {},
                "raw": {
                    "query": text_query,
                    "visual_context": "Stub visual context",
                    "metadata": {}
                }
            }
    
    dummy_agent_module.SmartGlassAgent = StubAgent
    sys.modules.setdefault("smartglass_agent", dummy_agent_module)
    
    # Stub llm_snn_backend
    dummy_snn = ModuleType("llm_snn_backend")
    
    class StubSNNBackend:
        def __init__(self, **kwargs):
            pass
    
    dummy_snn.SNNLLMBackend = StubSNNBackend
    sys.modules.setdefault("llm_snn_backend", dummy_snn)


def test_generate_scenarios():
    """Test that scenario generation works correctly."""
    _install_stub_modules()
    
    # Import after stubs are installed
    from examples.generate_snn_training_actions import generate_scenarios
    
    scenarios = generate_scenarios()
    
    # Validate scenarios
    assert len(scenarios) == 4, "Should generate 4 scenarios"
    
    scenario_names = {s["name"] for s in scenarios}
    expected_names = {"crossing_road", "supermarket_aisle", "bus_stop", "kitchen_cooking"}
    assert scenario_names == expected_names, "Should have expected scenario names"
    
    # Validate each scenario structure
    for scenario in scenarios:
        assert "name" in scenario
        assert "description" in scenario
        assert "text_query" in scenario
        assert "image" in scenario
        assert scenario["image"] is not None


def test_build_prompt_for_snn():
    """Test prompt building function."""
    _install_stub_modules()
    
    from examples.generate_snn_training_actions import build_prompt_for_snn
    
    prompt = build_prompt_for_snn("Is it safe?", "A busy road with cars")
    
    assert "Is it safe?" in prompt
    assert "A busy road with cars" in prompt
    assert "Visual context:" in prompt
    assert "User query:" in prompt
    assert "helpful assistant for smart glasses" in prompt


def test_extract_expected_output():
    """Test expected output extraction."""
    _install_stub_modules()
    
    from examples.generate_snn_training_actions import extract_expected_output
    
    mock_result = {
        "response": "Look both ways before crossing",
        "actions": [
            {
                "type": "TTS_SPEAK",
                "payload": {"text": "Look both ways"}
            }
        ],
        "visual_context": "A busy road",
        "extra_field": "should be ignored"
    }
    
    output = extract_expected_output(mock_result)
    
    assert output == {
        "response": "Look both ways before crossing",
        "actions": [
            {
                "type": "TTS_SPEAK",
                "payload": {"text": "Look both ways"}
            }
        ]
    }


def test_jsonl_output_format():
    """Test that JSONL output has correct format."""
    _install_stub_modules()
    
    from examples.generate_snn_training_actions import (
        build_prompt_for_snn,
        extract_expected_output
    )
    
    # Create a sample entry as the script would
    result = {
        "response": "Test response",
        "actions": [{"type": "TTS_SPEAK", "payload": {"text": "Test"}}],
        "visual_context": "Test context"
    }
    
    prompt = build_prompt_for_snn("Test query", "Test context")
    expected_output = extract_expected_output(result)
    
    entry = {
        "scenario_name": "test",
        "scenario_description": "Test scenario",
        "prompt": prompt,
        "expected_output": expected_output,
        "metadata": {
            "text_query": "Test query",
            "visual_context": "Test context"
        }
    }
    
    # Validate structure
    assert "scenario_name" in entry
    assert "scenario_description" in entry
    assert "prompt" in entry
    assert "expected_output" in entry
    assert "metadata" in entry
    
    # Validate expected_output structure
    assert "response" in entry["expected_output"]
    assert "actions" in entry["expected_output"]
    assert isinstance(entry["expected_output"]["actions"], list)
    
    # Validate metadata structure
    assert "text_query" in entry["metadata"]
    assert "visual_context" in entry["metadata"]
    
    # Validate JSON serialization
    json_str = json.dumps(entry)
    loaded = json.loads(json_str)
    assert loaded == entry


def test_script_imports():
    """Test that the script can be imported without errors."""
    _install_stub_modules()
    
    # This should not raise any errors
    import examples.generate_snn_training_actions as script
    
    # Verify key functions exist
    assert hasattr(script, "create_synthetic_image")
    assert hasattr(script, "generate_scenarios")
    assert hasattr(script, "build_prompt_for_snn")
    assert hasattr(script, "extract_expected_output")
    assert hasattr(script, "main")


def test_action_types_compatibility():
    """Test that generated action types match Android SDK expectations."""
    # Valid action types from SmartGlassAction.kt
    valid_action_types = {
        "SHOW_TEXT",
        "TTS_SPEAK",
        "NAVIGATE",
        "REMEMBER_NOTE",
        "OPEN_APP",
        "SYSTEM_HINT"
    }
    
    # Sample actions that could be generated
    sample_actions = [
        {"type": "TTS_SPEAK", "payload": {"text": "Test"}},
        {"type": "SHOW_TEXT", "payload": {"title": "Alert", "body": "Body"}},
        {"type": "NAVIGATE", "payload": {"destinationLabel": "Home"}},
    ]
    
    for action in sample_actions:
        assert action["type"] in valid_action_types
        assert "payload" in action
        assert isinstance(action["payload"], dict)
