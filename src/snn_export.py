"""Export utilities for SNN student models to mobile-friendly formats.

This module provides comprehensive export functionality for deploying trained
SNN student models on mobile platforms (Android/iOS) via TorchScript or ONNX.

Key Features:
- TorchScript export with JIT tracing for native PyTorch Mobile runtime
- ONNX export with dynamic axes for cross-platform deployment
- Defensive validation of model shapes, timesteps, and metadata
- Documented handling of SNN quirks (timesteps dimension, stateful layers)
- Automatic artifact organization in exports/ subdirectory

Example Usage:
    from src.snn_export import export_to_torchscript, export_to_onnx
    
    # After training, export both formats
    example_inputs = {"input_ids": torch.zeros((1, 4), dtype=torch.long)}
    
    export_to_torchscript(
        model_path="artifacts/snn_student/student.pt",
        output_path="artifacts/snn_student/exports/student_mobile.pt",
        example_inputs=example_inputs
    )
    
    export_to_onnx(
        model_path="artifacts/snn_student/student.pt",
        output_path="artifacts/snn_student/exports/student.onnx",
        example_inputs=example_inputs
    )

Mobile Runtime Integration:
    
    Android (TorchScript):
        - Add PyTorch Mobile to build.gradle:
          implementation 'org.pytorch:pytorch_android:2.0.0'
        - Load model: Module module = LiteModuleLoader.load(assetFilePath);
        - Run inference: IValue output = module.forward(IValue.from(inputTensor));
    
    Android (ONNX):
        - Add ONNX Runtime: implementation 'com.microsoft.onnxruntime:onnxruntime-android:1.16.0'
        - Load model: OrtSession session = env.createSession(modelPath);
        - Run inference: OnnxTensor inputTensor = ...; session.run(inputs);
    
    iOS (TorchScript):
        - Add PyTorch pod: pod 'LibTorch-Lite'
        - Load model: torch::jit::mobile::Module module = torch::jit::_load_for_mobile(modelPath);
        - Run inference: auto output = module.forward({inputTensor});

SNN-Specific Considerations:
    
    1. Timesteps Dimension:
       - Current SNN implementation processes sequence-level spikes without explicit timestep dimension
       - Models operate on [batch, seq_len] inputs, producing [batch, seq_len, vocab_size] outputs
       - For explicit temporal dynamics, consider modifying architecture to include [batch, timesteps, seq_len]
    
    2. Stateful Layers:
       - SpikingActivation uses surrogate gradients (sigmoid, fast_sigmoid, triangular, arctan)
       - These are stateless during inference (no hidden state reset needed between sequences)
       - For true stateful SNN layers (membrane potential tracking), implement reset() methods
    
    3. Mobile Optimization:
       - Export with eval mode to remove training-only operations (dropout, batch norm training behavior)
       - Consider quantization-aware training for INT8 deployment (<100mW power target)
       - Use smaller batch sizes (batch=1) for mobile inference
       - Pre-tokenize inputs on device to match training tokenizer (vocab_size must match)
    
    4. Performance Targets:
       - Latency: <50ms per inference on mobile devices
       - Power: <100mW during active inference
       - Model size: <5MB (student only, compressed)

Artifacts Organization:
    - Models are exported to: {artifact_dir}/exports/
    - TorchScript: student_mobile.pt
    - ONNX: student.onnx
    - Metadata: Export metadata appended to existing metadata.json
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any

import torch
from torch import nn


logger = logging.getLogger(__name__)


class ExportError(Exception):
    """Raised when model export fails validation or processing."""
    pass


def _validate_metadata(metadata_path: Path) -> Dict[str, Any]:
    """Load and validate metadata.json from training.
    
    Args:
        metadata_path: Path to metadata.json file
        
    Returns:
        Validated metadata dictionary
        
    Raises:
        ExportError: If metadata is missing or invalid
    """
    if not metadata_path.exists():
        raise ExportError(
            f"Metadata file not found: {metadata_path}\n"
            f"Ensure the model was trained with train_snn_student.py which generates metadata.json"
        )
    
    try:
        with metadata_path.open("r", encoding="utf-8") as f:
            metadata = json.load(f)
    except json.JSONDecodeError as e:
        raise ExportError(f"Failed to parse metadata.json: {e}")
    
    # Validate required fields
    required_fields = ["vocab_size", "model_type"]
    missing_fields = [field for field in required_fields if field not in metadata]
    if missing_fields:
        raise ExportError(
            f"Metadata missing required fields: {missing_fields}\n"
            f"Available fields: {list(metadata.keys())}"
        )
    
    return metadata


def _load_student_model(model_path: Path, metadata: Dict[str, Any], device: str = "cpu") -> nn.Module:
    """Load the trained student model from checkpoint.
    
    Args:
        model_path: Path to student.pt checkpoint
        metadata: Validated metadata dictionary
        device: Device to load model on (cpu/cuda)
        
    Returns:
        Loaded student model in eval mode
        
    Raises:
        ExportError: If model loading fails
    """
    if not model_path.exists():
        raise ExportError(
            f"Model checkpoint not found: {model_path}\n"
            f"Ensure the model was trained and student.pt exists"
        )
    
    try:
        # Import SpikingStudentLM from training script
        from scripts.train_snn_student import SpikingStudentLM, SNNConfig
    except ImportError as e:
        raise ExportError(
            f"Failed to import SpikingStudentLM: {e}\n"
            f"Ensure scripts/train_snn_student.py is available in Python path"
        )
    
    # Extract model configuration
    vocab_size = metadata["vocab_size"]
    architecture = metadata.get("architecture", {})
    snn_config_dict = metadata.get("snn_config", {})
    
    # Reconstruct SNNConfig
    snn_config = SNNConfig(
        num_timesteps=snn_config_dict.get("num_timesteps", 4),
        surrogate_type=snn_config_dict.get("surrogate_type", "sigmoid"),
        spike_threshold=snn_config_dict.get("spike_threshold", 1.0),
    )
    
    # Initialize model with same architecture as training
    model = SpikingStudentLM(
        vocab_size=vocab_size,
        dim=architecture.get("dim", 128),
        depth=architecture.get("depth", 2),
        num_heads=architecture.get("num_heads", 4),
        snn_config=snn_config,
    )
    
    # Load trained weights
    try:
        state_dict = torch.load(model_path, map_location=device)
        model.load_state_dict(state_dict)
    except Exception as e:
        raise ExportError(f"Failed to load model weights from {model_path}: {e}")
    
    model.eval()
    model.to(device)
    
    logger.info(f"Loaded student model: {metadata['model_type']} with {vocab_size} vocab size")
    logger.info(f"SNN config: timesteps={snn_config.num_timesteps}, "
                f"surrogate={snn_config.surrogate_type}, threshold={snn_config.spike_threshold}")
    
    return model


def _validate_example_inputs(
    example_inputs: Dict[str, torch.Tensor],
    vocab_size: int,
    metadata: Dict[str, Any]
) -> None:
    """Validate example inputs for export.
    
    Args:
        example_inputs: Dictionary with "input_ids" tensor
        vocab_size: Expected vocabulary size
        metadata: Model metadata for additional validation
        
    Raises:
        ExportError: If inputs are invalid
    """
    if "input_ids" not in example_inputs:
        raise ExportError(
            f"example_inputs must contain 'input_ids' key, got: {list(example_inputs.keys())}"
        )
    
    input_ids = example_inputs["input_ids"]
    
    if not isinstance(input_ids, torch.Tensor):
        raise ExportError(
            f"input_ids must be a torch.Tensor, got: {type(input_ids)}"
        )
    
    if input_ids.dtype != torch.long:
        raise ExportError(
            f"input_ids must be torch.long dtype, got: {input_ids.dtype}"
        )
    
    if input_ids.ndim != 2:
        raise ExportError(
            f"input_ids must be 2D [batch, seq_len], got shape: {input_ids.shape}"
        )
    
    batch_size, seq_len = input_ids.shape
    if batch_size < 1 or seq_len < 1:
        raise ExportError(
            f"input_ids must have batch_size >= 1 and seq_len >= 1, got: {input_ids.shape}"
        )
    
    # Check for out-of-vocabulary tokens
    if torch.any(input_ids >= vocab_size) or torch.any(input_ids < 0):
        raise ExportError(
            f"input_ids contains out-of-vocabulary tokens. "
            f"Valid range: [0, {vocab_size}), got min={input_ids.min()}, max={input_ids.max()}"
        )
    
    # SNN-specific validation
    snn_config = metadata.get("snn_config", {})
    timesteps = snn_config.get("num_timesteps", 4)
    
    logger.info(f"Validated example inputs: shape={input_ids.shape}, "
                f"vocab_size={vocab_size}, snn_timesteps={timesteps}")
    logger.info(f"Note: SNN timesteps are handled internally by SpikingActivation layers, "
                f"not as explicit input dimension")


def export_to_torchscript(
    output_path: str,
    example_inputs: Dict[str, torch.Tensor],
    model_path: Optional[str] = None,
    metadata_path: Optional[str] = None,
    optimize_for_mobile: bool = True,
) -> Path:
    """Export trained SNN student model to TorchScript for PyTorch Mobile runtime.
    
    TorchScript provides the most seamless integration with PyTorch Mobile on Android/iOS.
    The exported model runs with native PyTorch operators, supporting the full model architecture
    including custom SNN layers (SpikingActivation with surrogate gradients).
    
    Args:
        output_path: Destination path for .pt TorchScript file
        example_inputs: Dictionary with "input_ids" key containing torch.Tensor of shape [batch, seq_len]
        model_path: Path to student.pt checkpoint (default: infer from output_path)
        metadata_path: Path to metadata.json (default: infer from model_path)
        optimize_for_mobile: Apply mobile-specific optimizations (default: True)
        
    Returns:
        Path object pointing to exported TorchScript file
        
    Raises:
        ExportError: If export fails validation or processing
        
    Example:
        >>> import torch
        >>> from src.snn_export import export_to_torchscript
        >>> 
        >>> example_inputs = {"input_ids": torch.zeros((1, 4), dtype=torch.long)}
        >>> export_to_torchscript(
        ...     output_path="artifacts/snn_student/exports/student_mobile.pt",
        ...     example_inputs=example_inputs
        ... )
        
    Mobile Integration:
        Android:
            ```java
            // Load model
            Module module = LiteModuleLoader.load("student_mobile.pt");
            
            // Prepare input
            long[] inputIds = {101, 2054, 2003, 102};  // tokenized text
            Tensor inputTensor = Tensor.fromBlob(inputIds, new long[]{1, 4});
            
            // Run inference
            IValue output = module.forward(IValue.from(inputTensor));
            Tensor logits = output.toTensor();  // [1, 4, vocab_size]
            ```
        
        iOS:
            ```swift
            // Load model
            guard let module = try? TorchModule(fileAtPath: modelPath) else { return }
            
            // Prepare input
            let inputIds: [Int64] = [101, 2054, 2003, 102]
            let inputTensor = Tensor(shape: [1, 4], data: inputIds)
            
            // Run inference
            guard let outputTensor = module.forward(inputTensor) else { return }
            // outputTensor shape: [1, 4, vocab_size]
            ```
    """
    output_path = Path(output_path)
    
    # Infer paths if not provided
    if model_path is None:
        # Infer from output_path: artifacts/snn_student/exports/student_mobile.pt -> ../student.pt
        artifact_dir = output_path.parent.parent
        model_path = artifact_dir / "student.pt"
    else:
        model_path = Path(model_path)
    
    if metadata_path is None:
        metadata_path = model_path.with_name("metadata.json")
    else:
        metadata_path = Path(metadata_path)
    
    logger.info(f"Starting TorchScript export from {model_path} to {output_path}")
    
    # Validate metadata
    metadata = _validate_metadata(metadata_path)
    vocab_size = metadata["vocab_size"]
    
    # Validate example inputs
    _validate_example_inputs(example_inputs, vocab_size, metadata)
    
    # Load model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = _load_student_model(model_path, metadata, device)
    
    # Move example inputs to same device as model
    input_ids = example_inputs["input_ids"].to(device)
    
    # Export via JIT trace
    try:
        logger.info("Tracing model with JIT compiler...")
        traced_model = torch.jit.trace(model, input_ids)
        
        # Optimize for mobile if requested
        if optimize_for_mobile:
            try:
                from torch.utils.mobile_optimizer import optimize_for_mobile
                logger.info("Applying mobile optimizations...")
                traced_model = optimize_for_mobile(traced_model)
            except ImportError:
                logger.warning("torch.utils.mobile_optimizer not available, skipping mobile optimization")
        
    except Exception as e:
        raise ExportError(f"Failed to trace model with TorchScript: {e}")
    
    # Create output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save traced model
    try:
        traced_model.save(str(output_path))
    except Exception as e:
        raise ExportError(f"Failed to save TorchScript model to {output_path}: {e}")
    
    # Verify export by loading
    try:
        loaded_model = torch.jit.load(str(output_path), map_location=device)
        with torch.no_grad():
            test_output = loaded_model(input_ids)
        logger.info(f"Verified exported model: output shape {test_output.shape}")
    except Exception as e:
        raise ExportError(f"Failed to verify exported model: {e}")
    
    # Update metadata with export info
    _update_metadata_with_export(metadata_path, output_path, "torchscript", metadata)
    
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"✓ Successfully exported TorchScript model to {output_path}")
    logger.info(f"  File size: {file_size_mb:.2f} MB")
    logger.info(f"  Mobile optimized: {optimize_for_mobile}")
    logger.info(f"  Input shape: {input_ids.shape}")
    logger.info(f"  Output shape: {test_output.shape}")
    
    return output_path


def export_to_onnx(
    output_path: str,
    example_inputs: Dict[str, torch.Tensor],
    model_path: Optional[str] = None,
    metadata_path: Optional[str] = None,
    opset_version: int = 17,
    dynamic_axes: bool = True,
) -> Path:
    """Export trained SNN student model to ONNX for cross-platform deployment.
    
    ONNX provides broader runtime support including ONNX Runtime Mobile (Android/iOS),
    TensorFlow Lite (via ONNX-TF), and CoreML (via onnx-coreml). The exported model
    can run on devices without PyTorch installed.
    
    Args:
        output_path: Destination path for .onnx file
        example_inputs: Dictionary with "input_ids" key containing torch.Tensor of shape [batch, seq_len]
        model_path: Path to student.pt checkpoint (default: infer from output_path)
        metadata_path: Path to metadata.json (default: infer from model_path)
        opset_version: ONNX opset version (default: 17 for broad compatibility)
        dynamic_axes: Enable dynamic batch and sequence length (default: True)
        
    Returns:
        Path object pointing to exported ONNX file
        
    Raises:
        ExportError: If export fails validation or processing
        
    Example:
        >>> import torch
        >>> from src.snn_export import export_to_onnx
        >>> 
        >>> example_inputs = {"input_ids": torch.zeros((1, 4), dtype=torch.long)}
        >>> export_to_onnx(
        ...     output_path="artifacts/snn_student/exports/student.onnx",
        ...     example_inputs=example_inputs
        ... )
        
    Mobile Integration:
        Android (ONNX Runtime):
            ```java
            // Load model
            OrtEnvironment env = OrtEnvironment.getEnvironment();
            OrtSession session = env.createSession(modelPath);
            
            // Prepare input
            long[] inputIds = {101, 2054, 2003, 102};
            long[] shape = {1, 4};
            OnnxTensor inputTensor = OnnxTensor.createTensor(env, 
                LongBuffer.wrap(inputIds), shape);
            
            // Run inference
            Map<String, OnnxTensor> inputs = Map.of("input_ids", inputTensor);
            OrtSession.Result output = session.run(inputs);
            float[][][] logits = (float[][][]) output.get(0).getValue();
            ```
        
        iOS (ONNX Runtime):
            ```swift
            // Load model
            let env = try ORTEnv(loggingLevel: .warning)
            let session = try ORTSession(env: env, modelPath: modelPath)
            
            // Prepare input
            let inputIds: [Int64] = [101, 2054, 2003, 102]
            let shape = [1, 4]
            let inputTensor = try ORTValue(tensorData: Data(...), 
                                          elementType: .int64, shape: shape)
            
            // Run inference
            let outputs = try session.run(withInputs: ["input_ids": inputTensor])
            let logits = outputs["logits"]
            ```
    """
    output_path = Path(output_path)
    
    # Infer paths if not provided
    if model_path is None:
        artifact_dir = output_path.parent.parent
        model_path = artifact_dir / "student.pt"
    else:
        model_path = Path(model_path)
    
    if metadata_path is None:
        metadata_path = model_path.with_name("metadata.json")
    else:
        metadata_path = Path(metadata_path)
    
    logger.info(f"Starting ONNX export from {model_path} to {output_path}")
    
    # Validate metadata
    metadata = _validate_metadata(metadata_path)
    vocab_size = metadata["vocab_size"]
    
    # Validate example inputs
    _validate_example_inputs(example_inputs, vocab_size, metadata)
    
    # Load model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = _load_student_model(model_path, metadata, device)
    
    # Move example inputs to CPU for ONNX export (ONNX typically expects CPU tensors)
    input_ids = example_inputs["input_ids"].cpu()
    model = model.cpu()
    
    # Configure dynamic axes
    dynamic_axes_config = None
    if dynamic_axes:
        dynamic_axes_config = {
            "input_ids": {0: "batch", 1: "seq_len"},
            "logits": {0: "batch", 1: "seq_len"},
        }
    
    # Create output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Export to ONNX
    try:
        logger.info(f"Exporting to ONNX (opset_version={opset_version}, dynamic_axes={dynamic_axes})...")
        torch.onnx.export(
            model,
            input_ids,
            str(output_path),
            input_names=["input_ids"],
            output_names=["logits"],
            dynamic_axes=dynamic_axes_config,
            opset_version=opset_version,
            do_constant_folding=True,
            export_params=True,
        )
    except Exception as e:
        raise ExportError(f"Failed to export model to ONNX: {e}")
    
    # Verify ONNX model
    try:
        import onnx
        onnx_model = onnx.load(str(output_path))
        onnx.checker.check_model(onnx_model)
        logger.info("✓ ONNX model validation passed")
        
        # Log model info
        graph = onnx_model.graph
        logger.info(f"  Inputs: {[input.name for input in graph.input]}")
        logger.info(f"  Outputs: {[output.name for output in graph.output]}")
        logger.info(f"  Opset version: {opset_version}")
        
    except ImportError:
        logger.warning("onnx package not available for verification, skipping validation")
    except Exception as e:
        raise ExportError(f"ONNX model validation failed: {e}")
    
    # Test inference with ONNX Runtime if available
    try:
        import onnxruntime as ort
        logger.info("Testing ONNX Runtime inference...")
        
        session = ort.InferenceSession(str(output_path))
        input_name = session.get_inputs()[0].name
        output_name = session.get_outputs()[0].name
        
        # Run inference
        ort_inputs = {input_name: input_ids.numpy()}
        ort_outputs = session.run([output_name], ort_inputs)
        
        logger.info(f"✓ ONNX Runtime inference test passed")
        logger.info(f"  Input shape: {input_ids.shape}")
        logger.info(f"  Output shape: {ort_outputs[0].shape}")
        
    except ImportError:
        logger.warning("onnxruntime not available for inference test, skipping")
    except Exception as e:
        logger.warning(f"ONNX Runtime inference test failed (non-fatal): {e}")
    
    # Update metadata with export info
    _update_metadata_with_export(metadata_path, output_path, "onnx", metadata)
    
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"✓ Successfully exported ONNX model to {output_path}")
    logger.info(f"  File size: {file_size_mb:.2f} MB")
    logger.info(f"  Opset version: {opset_version}")
    logger.info(f"  Dynamic axes: {dynamic_axes}")
    
    return output_path


def _update_metadata_with_export(
    metadata_path: Path,
    export_path: Path,
    export_format: str,
    existing_metadata: Dict[str, Any]
) -> None:
    """Update metadata.json with export information.
    
    Args:
        metadata_path: Path to metadata.json
        export_path: Path to exported model file
        export_format: Export format ("torchscript" or "onnx")
        existing_metadata: Current metadata dictionary
    """
    try:
        # Add export info
        if "exports" not in existing_metadata:
            existing_metadata["exports"] = []
        
        export_info = {
            "format": export_format,
            "path": str(export_path),
            "timestamp": datetime.now().astimezone().isoformat(),
            "file_size_bytes": export_path.stat().st_size,
        }
        
        # Update or append
        updated = False
        for i, exp in enumerate(existing_metadata["exports"]):
            if exp.get("format") == export_format:
                existing_metadata["exports"][i] = export_info
                updated = True
                break
        
        if not updated:
            existing_metadata["exports"].append(export_info)
        
        # Write updated metadata
        with metadata_path.open("w", encoding="utf-8") as f:
            json.dump(existing_metadata, f, indent=2)
        
        logger.info(f"Updated metadata.json with {export_format} export info")
        
    except Exception as e:
        logger.warning(f"Failed to update metadata with export info: {e}")


def load_and_export(
    artifact_dir: str,
    export_formats: list[str] = ["torchscript", "onnx"],
    example_seq_len: int = 4,
) -> Dict[str, Path]:
    """Convenience function to load a trained model and export in multiple formats.
    
    Args:
        artifact_dir: Directory containing student.pt and metadata.json
        export_formats: List of formats to export ("torchscript", "onnx", or both)
        example_seq_len: Sequence length for example inputs (default: 4)
        
    Returns:
        Dictionary mapping format name to exported file path
        
    Example:
        >>> from src.snn_export import load_and_export
        >>> 
        >>> paths = load_and_export(
        ...     artifact_dir="artifacts/snn_student",
        ...     export_formats=["torchscript", "onnx"]
        ... )
        >>> print(paths)
        {'torchscript': PosixPath('.../exports/student_mobile.pt'),
         'onnx': PosixPath('.../exports/student.onnx')}
    """
    artifact_dir = Path(artifact_dir)
    exports_dir = artifact_dir / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    
    # Load metadata to get vocab_size
    metadata_path = artifact_dir / "metadata.json"
    metadata = _validate_metadata(metadata_path)
    vocab_size = metadata["vocab_size"]
    
    # Create example inputs
    example_inputs = {
        "input_ids": torch.zeros((1, example_seq_len), dtype=torch.long)
    }
    
    exported_paths = {}
    
    for fmt in export_formats:
        if fmt == "torchscript":
            output_path = exports_dir / "student_mobile.pt"
            exported_paths["torchscript"] = export_to_torchscript(
                output_path=str(output_path),
                example_inputs=example_inputs,
                model_path=str(artifact_dir / "student.pt"),
                metadata_path=str(metadata_path),
            )
        elif fmt == "onnx":
            output_path = exports_dir / "student.onnx"
            exported_paths["onnx"] = export_to_onnx(
                output_path=str(output_path),
                example_inputs=example_inputs,
                model_path=str(artifact_dir / "student.pt"),
                metadata_path=str(metadata_path),
            )
        else:
            logger.warning(f"Unknown export format: {fmt}, skipping")
    
    return exported_paths


__all__ = [
    "export_to_torchscript",
    "export_to_onnx",
    "load_and_export",
    "ExportError",
]
