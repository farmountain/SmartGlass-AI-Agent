"""Tests for src/snn_export.py - SNN student model export utilities."""

import importlib.util
import json
import sys
from pathlib import Path

try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False
    # Mock pytest.skip for standalone execution
    class MockPytest:
        @staticmethod
        def skip(msg):
            pass
        
        class mark:
            @staticmethod
            def skipif(condition, reason=""):
                def decorator(func):
                    return func
                return decorator
    
    pytest = MockPytest()

# Check for required dependencies
REQUIRED_MODULES = ["torch"]


def _has_required_dependencies() -> bool:
    """Check if required dependencies are available."""
    missing = []
    for name in REQUIRED_MODULES:
        if importlib.util.find_spec(name) is None:
            missing.append(name)
    
    # Also check if training script is available
    try:
        from scripts.train_snn_student import SpikingStudentLM, SNNConfig
    except ImportError:
        missing.append("scripts.train_snn_student")
    
    if missing:
        if HAS_PYTEST:
            pytest.skip(f"Missing dependencies for SNN export tests: {', '.join(missing)}")
        return False
    return True


# Only import torch if available (after dependency check)
def _import_torch():
    """Import torch after dependency check."""
    import torch
    return torch


def _import_training_modules():
    """Import training modules after dependency check."""
    from scripts.train_snn_student import SpikingStudentLM, SNNConfig
    return SpikingStudentLM, SNNConfig


@pytest.mark.skipif(not _has_required_dependencies(), reason="Missing required dependencies")
def test_export_to_torchscript_smoke(tmp_path: Path) -> None:
    """Test TorchScript export with minimal model."""
    torch = _import_torch()
    SpikingStudentLM, SNNConfig = _import_training_modules()
    from src.snn_export import export_to_torchscript
    
    vocab_size = 100
    
    # Create and save a minimal student model
    snn_config = SNNConfig(num_timesteps=4, surrogate_type="sigmoid", spike_threshold=1.0)
    model = SpikingStudentLM(vocab_size=vocab_size, dim=32, depth=1, num_heads=2, snn_config=snn_config)
    
    model_path = tmp_path / "student.pt"
    torch.save(model.state_dict(), model_path)
    
    # Create metadata
    metadata = {
        "vocab_size": vocab_size,
        "model_type": "SpikingStudentLM",
        "architecture": {"dim": 32, "depth": 1, "num_heads": 2},
        "snn_config": {
            "num_timesteps": 4,
            "surrogate_type": "sigmoid",
            "spike_threshold": 1.0,
        },
    }
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(json.dumps(metadata))
    
    # Export to TorchScript
    output_path = tmp_path / "exports" / "student_mobile.pt"
    example_inputs = {"input_ids": torch.zeros((1, 4), dtype=torch.long)}
    
    result = export_to_torchscript(
        output_path=str(output_path),
        example_inputs=example_inputs,
        model_path=str(model_path),
        metadata_path=str(metadata_path),
    )
    
    # Verify export
    assert result.exists(), "TorchScript export did not produce a file"
    assert result.stat().st_size > 0, "TorchScript export is empty"
    
    # Verify it can be loaded
    loaded_model = torch.jit.load(str(result), map_location="cpu")
    assert loaded_model is not None
    
    # Verify inference works
    with torch.no_grad():
        output = loaded_model(example_inputs["input_ids"])
    assert output.shape == (1, 4, vocab_size), f"Expected shape (1, 4, {vocab_size}), got {output.shape}"
    
    print("✓ TorchScript export test passed")


@pytest.mark.skipif(not _has_required_dependencies(), reason="Missing required dependencies")
def test_export_to_onnx_smoke(tmp_path: Path) -> None:
    """Test ONNX export with minimal model."""
    torch = _import_torch()
    SpikingStudentLM, SNNConfig = _import_training_modules()
    from src.snn_export import export_to_onnx
    
    vocab_size = 100
    
    # Create and save a minimal student model
    snn_config = SNNConfig(num_timesteps=4, surrogate_type="sigmoid", spike_threshold=1.0)
    model = SpikingStudentLM(vocab_size=vocab_size, dim=32, depth=1, num_heads=2, snn_config=snn_config)
    
    model_path = tmp_path / "student.pt"
    torch.save(model.state_dict(), model_path)
    
    # Create metadata
    metadata = {
        "vocab_size": vocab_size,
        "model_type": "SpikingStudentLM",
        "architecture": {"dim": 32, "depth": 1, "num_heads": 2},
        "snn_config": {
            "num_timesteps": 4,
            "surrogate_type": "sigmoid",
            "spike_threshold": 1.0,
        },
    }
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(json.dumps(metadata))
    
    # Export to ONNX
    output_path = tmp_path / "exports" / "student.onnx"
    example_inputs = {"input_ids": torch.zeros((1, 4), dtype=torch.long)}
    
    result = export_to_onnx(
        output_path=str(output_path),
        example_inputs=example_inputs,
        model_path=str(model_path),
        metadata_path=str(metadata_path),
    )
    
    # Verify export
    assert result.exists(), "ONNX export did not produce a file"
    assert result.stat().st_size > 0, "ONNX export is empty"
    
    # Verify ONNX model structure
    try:
        import onnx
        onnx_model = onnx.load(str(result))
        onnx.checker.check_model(onnx_model)
        
        # Check inputs/outputs
        graph = onnx_model.graph
        input_names = [inp.name for inp in graph.input]
        output_names = [out.name for out in graph.output]
        
        assert "input_ids" in input_names, f"Expected 'input_ids' in inputs, got {input_names}"
        assert "logits" in output_names, f"Expected 'logits' in outputs, got {output_names}"
        
        print("✓ ONNX model validation passed")
    except ImportError:
        print("⚠ onnx package not available, skipping validation")
    
    # Try inference with ONNX Runtime if available
    try:
        import onnxruntime as ort
        session = ort.InferenceSession(str(result))
        
        input_name = session.get_inputs()[0].name
        output_name = session.get_outputs()[0].name
        
        ort_inputs = {input_name: example_inputs["input_ids"].numpy()}
        ort_outputs = session.run([output_name], ort_inputs)
        
        assert ort_outputs[0].shape == (1, 4, vocab_size), \
            f"Expected shape (1, 4, {vocab_size}), got {ort_outputs[0].shape}"
        
        print("✓ ONNX Runtime inference test passed")
    except ImportError:
        print("⚠ onnxruntime not available, skipping inference test")
    
    print("✓ ONNX export test passed")


@pytest.mark.skipif(not _has_required_dependencies(), reason="Missing required dependencies")
def test_load_and_export(tmp_path: Path) -> None:
    """Test convenience function that exports both formats."""
    torch = _import_torch()
    SpikingStudentLM, SNNConfig = _import_training_modules()
    from src.snn_export import load_and_export
    
    vocab_size = 100
    
    # Create and save a minimal student model
    snn_config = SNNConfig(num_timesteps=4, surrogate_type="sigmoid", spike_threshold=1.0)
    model = SpikingStudentLM(vocab_size=vocab_size, dim=32, depth=1, num_heads=2, snn_config=snn_config)
    
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    
    model_path = artifact_dir / "student.pt"
    torch.save(model.state_dict(), model_path)
    
    # Create metadata
    metadata = {
        "vocab_size": vocab_size,
        "model_type": "SpikingStudentLM",
        "architecture": {"dim": 32, "depth": 1, "num_heads": 2},
        "snn_config": {
            "num_timesteps": 4,
            "surrogate_type": "sigmoid",
            "spike_threshold": 1.0,
        },
    }
    metadata_path = artifact_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata))
    
    # Export both formats
    paths = load_and_export(
        artifact_dir=str(artifact_dir),
        export_formats=["torchscript", "onnx"],
        example_seq_len=4,
    )
    
    # Verify both exports
    assert "torchscript" in paths, "TorchScript export missing from results"
    assert "onnx" in paths, "ONNX export missing from results"
    
    assert paths["torchscript"].exists(), "TorchScript file not created"
    assert paths["onnx"].exists(), "ONNX file not created"
    
    # Check metadata was updated
    updated_metadata = json.loads(metadata_path.read_text())
    assert "exports" in updated_metadata, "Metadata not updated with export info"
    assert len(updated_metadata["exports"]) == 2, "Expected 2 export entries in metadata"
    
    print("✓ load_and_export test passed")


@pytest.mark.skipif(not _has_required_dependencies(), reason="Missing required dependencies")
def test_export_validation_errors(tmp_path: Path) -> None:
    """Test that export validates inputs and raises meaningful errors."""
    torch = _import_torch()
    SpikingStudentLM, SNNConfig = _import_training_modules()
    from src.snn_export import export_to_torchscript, ExportError
    
    # Test missing metadata
    try:
        example_inputs = {"input_ids": torch.zeros((1, 4), dtype=torch.long)}
        export_to_torchscript(
            output_path=str(tmp_path / "out.pt"),
            example_inputs=example_inputs,
            model_path=str(tmp_path / "nonexistent.pt"),
            metadata_path=str(tmp_path / "nonexistent.json"),
        )
        assert False, "Expected ExportError for missing metadata"
    except ExportError as e:
        assert "Metadata file not found" in str(e)
        print(f"✓ Correctly caught missing metadata: {e}")
    
    # Create metadata but missing model
    vocab_size = 100
    metadata = {
        "vocab_size": vocab_size,
        "model_type": "SpikingStudentLM",
        "architecture": {"dim": 32, "depth": 1, "num_heads": 2},
        "snn_config": {"num_timesteps": 4, "surrogate_type": "sigmoid", "spike_threshold": 1.0},
    }
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(json.dumps(metadata))
    
    try:
        example_inputs = {"input_ids": torch.zeros((1, 4), dtype=torch.long)}
        export_to_torchscript(
            output_path=str(tmp_path / "out.pt"),
            example_inputs=example_inputs,
            model_path=str(tmp_path / "nonexistent.pt"),
            metadata_path=str(metadata_path),
        )
        assert False, "Expected ExportError for missing model"
    except ExportError as e:
        assert "Model checkpoint not found" in str(e)
        print(f"✓ Correctly caught missing model: {e}")
    
    # Test invalid input shape
    snn_config = SNNConfig(num_timesteps=4, surrogate_type="sigmoid", spike_threshold=1.0)
    model = SpikingStudentLM(vocab_size=vocab_size, dim=32, depth=1, num_heads=2, snn_config=snn_config)
    model_path = tmp_path / "student.pt"
    torch.save(model.state_dict(), model_path)
    
    try:
        # 1D input instead of 2D
        example_inputs = {"input_ids": torch.zeros((4,), dtype=torch.long)}
        export_to_torchscript(
            output_path=str(tmp_path / "out.pt"),
            example_inputs=example_inputs,
            model_path=str(model_path),
            metadata_path=str(metadata_path),
        )
        assert False, "Expected ExportError for wrong input shape"
    except ExportError as e:
        assert "must be 2D" in str(e)
        print(f"✓ Correctly caught invalid shape: {e}")
    
    # Test out of vocabulary tokens
    try:
        # Token IDs beyond vocab_size
        example_inputs = {"input_ids": torch.tensor([[0, 1, vocab_size + 10, 3]], dtype=torch.long)}
        export_to_torchscript(
            output_path=str(tmp_path / "out.pt"),
            example_inputs=example_inputs,
            model_path=str(model_path),
            metadata_path=str(metadata_path),
        )
        assert False, "Expected ExportError for out-of-vocab tokens"
    except ExportError as e:
        assert "out-of-vocabulary" in str(e)
        print(f"✓ Correctly caught out-of-vocab tokens: {e}")
    
    print("✓ Export validation test passed")


@pytest.mark.skipif(not _has_required_dependencies(), reason="Missing required dependencies")
def test_metadata_update(tmp_path: Path) -> None:
    """Test that metadata.json is updated with export information."""
    torch = _import_torch()
    SpikingStudentLM, SNNConfig = _import_training_modules()
    from src.snn_export import export_to_torchscript
    
    vocab_size = 100
    
    # Create and save model
    snn_config = SNNConfig(num_timesteps=4, surrogate_type="sigmoid", spike_threshold=1.0)
    model = SpikingStudentLM(vocab_size=vocab_size, dim=32, depth=1, num_heads=2, snn_config=snn_config)
    
    model_path = tmp_path / "student.pt"
    torch.save(model.state_dict(), model_path)
    
    # Create metadata
    metadata = {
        "vocab_size": vocab_size,
        "model_type": "SpikingStudentLM",
        "architecture": {"dim": 32, "depth": 1, "num_heads": 2},
        "snn_config": {"num_timesteps": 4, "surrogate_type": "sigmoid", "spike_threshold": 1.0},
    }
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(json.dumps(metadata))
    
    # Export
    output_path = tmp_path / "exports" / "student_mobile.pt"
    example_inputs = {"input_ids": torch.zeros((1, 4), dtype=torch.long)}
    
    export_to_torchscript(
        output_path=str(output_path),
        example_inputs=example_inputs,
        model_path=str(model_path),
        metadata_path=str(metadata_path),
    )
    
    # Check metadata was updated
    updated_metadata = json.loads(metadata_path.read_text())
    assert "exports" in updated_metadata, "Metadata should have 'exports' field"
    assert len(updated_metadata["exports"]) > 0, "Exports list should not be empty"
    
    export_info = updated_metadata["exports"][0]
    assert export_info["format"] == "torchscript", "Export format should be 'torchscript'"
    assert "timestamp" in export_info, "Export info should have timestamp"
    assert "file_size_bytes" in export_info, "Export info should have file_size_bytes"
    assert export_info["file_size_bytes"] > 0, "File size should be positive"
    
    print("✓ Metadata update test passed")


if __name__ == "__main__":
    # Run tests manually (requires torch to be installed)
    import tempfile
    
    try:
        torch = _import_torch()
        SpikingStudentLM, SNNConfig = _import_training_modules()
    except (ImportError, ModuleNotFoundError) as e:
        print(f"⚠ Skipping tests: {e}")
        print("Install torch and transformers to run these tests")
        sys.exit(0)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        print("\n=== Running TorchScript export test ===")
        test_export_to_torchscript_smoke(tmp_path / "test1")
        
        print("\n=== Running ONNX export test ===")
        test_export_to_onnx_smoke(tmp_path / "test2")
        
        print("\n=== Running load_and_export test ===")
        test_load_and_export(tmp_path / "test3")
        
        print("\n=== Running validation error tests ===")
        test_export_validation_errors(tmp_path / "test4")
        
        print("\n=== Running metadata update test ===")
        test_metadata_update(tmp_path / "test5")
        
        print("\n✓✓✓ All tests passed! ✓✓✓")
