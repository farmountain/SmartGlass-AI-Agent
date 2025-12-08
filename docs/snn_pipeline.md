# Teacher–Student SNN training guide

This guide walks through running `scripts/train_snn_student.py` with transformer teachers (from tiny GPT-2 to Llama-3.2-3B or Qwen-2.5-3B), the artifacts it produces, and how `SNNLLMBackend` consumes them.

## Prerequisites
- Python environment with `torch` plus `transformers` for the teacher model. `datasets` is only needed for non-synthetic datasets.
- GPU is optional; the script autodetects CUDA and otherwise runs on CPU.
- For larger teachers (Llama-3.2-3B, Qwen-2.5-3B), GPU with 16GB+ VRAM is recommended.

## Quickstart: distill a tiny GPT-2 teacher
Run a short training loop using a small, fast teacher (`sshleifer/tiny-gpt2`) and the synthetic prompt set:

```bash
python scripts/train_snn_student.py \
  --teacher-model sshleifer/tiny-gpt2 \
  --dataset synthetic \
  --num-steps 50 \
  --batch-size 4 \
  --grad-accum-steps 2 \
  --output-dir artifacts/snn_student_demo
```

## Production training with larger teachers

### Llama-3.2-3B Teacher
For production-quality distillation from Llama-3.2-3B:

```bash
python scripts/train_snn_student.py \
  --teacher-model meta-llama/Llama-3.2-3B \
  --dataset wikitext-2 \
  --num-steps 10000 \
  --batch-size 4 \
  --grad-accum-steps 8 \
  --max-length 512 \
  --lr 3e-4 \
  --scheduler cosine \
  --warmup-steps 500 \
  --snn-timesteps 8 \
  --snn-surrogate fast_sigmoid \
  --snn-threshold 0.5 \
  --output-dir artifacts/snn_student_llama
```

### Qwen-2.5-3B Teacher
For Qwen-2.5-3B with longer context:

```bash
python scripts/train_snn_student.py \
  --teacher-model Qwen/Qwen2.5-3B \
  --dataset wikitext-2 \
  --num-steps 10000 \
  --batch-size 2 \
  --grad-accum-steps 16 \
  --max-length 1024 \
  --scheduler linear \
  --warmup-steps 1000 \
  --snn-timesteps 8 \
  --snn-surrogate arctan \
  --output-dir artifacts/snn_student_qwen
```

## Configuration options

### Basic Training Parameters
- `--teacher-model`: Any Hugging Face causal LM ID or local path. Required.
- `--dataset`: `synthetic` (built-in prompts) or any `datasets`-compatible ID such as `wikitext-2`.
- `--dataset-path`: Plain-text prompts file (one prompt per line) if you prefer local data.
- `--output-dir`: Where to write artifacts (default: `artifacts/snn_student`).
- `--num-steps`, `--batch-size`, `--grad-accum-steps`: Training loop controls.
- `--max-length`: Maximum sequence length (default: 64, use 512-1024 for larger teachers).
- `--lr`: Learning rate (default: 1e-4, consider 3e-4 for larger runs).
- `--temperature`: Distillation temperature (default: 1.0).

### Learning Rate Scheduling
- `--scheduler {constant,cosine,linear}`: LR schedule type (default: constant).
  - `constant`: No scheduling (default for demos)
  - `cosine`: Cosine annealing with optional warmup
  - `linear`: Linear decay with optional warmup
- `--warmup-steps`: Number of warmup steps for LR scheduler (default: 0).

### SNN-Specific Hyperparameters
- `--snn-timesteps`: Number of simulation timesteps for spiking neurons (default: 4, use 8-16 for production).
- `--snn-surrogate {sigmoid,fast_sigmoid,triangular,arctan}`: Surrogate gradient function (default: sigmoid).
  - `sigmoid`: Smooth sigmoid derivative (stable, default)
  - `fast_sigmoid`: Faster approximation with limited range
  - `triangular`: Piecewise linear triangle function
  - `arctan`: Arctan-based smooth function
- `--snn-threshold`: Spike threshold for spiking neurons (default: 1.0, tune 0.5-1.5).

### Metadata and Logging
- `--log-interval`: Steps between loss logs, 0 to disable (default: 5).
- `--no-git-tracking`: Disable git commit tracking in metadata.
- `--export-format {none,torchscript,onnx}`: Export format for mobile deployment (default: none).
  - `none`: Skip export (default for faster training iterations)
  - `torchscript`: Export for PyTorch Mobile runtime (Android/iOS)
  - `onnx`: Export for ONNX Runtime Mobile (cross-platform)
- `--export-onnx`: DEPRECATED - Use `--export-format onnx` instead.

During training, the teacher is kept in eval mode and only the student updates. Loss logs appear every `--log-interval` steps.

## Artifact layout
After finishing the requested steps, the script writes artifacts under `--output-dir` (created if missing):

- `student.pt`: The student weights. Saved with `torch.save` state dict.
- `metadata.json`: A comprehensive JSON blob with model configuration, training hyperparameters, and results.
- `exports/` (optional): Mobile export artifacts (created when using `--export-format`)
  - `student_mobile.pt`: TorchScript model for PyTorch Mobile
  - `student.onnx`: ONNX model for ONNX Runtime Mobile

Example tree (with exports):

```
artifacts/snn_student_llama/
├── metadata.json
├── student.pt
└── exports/
    ├── student_mobile.pt  (TorchScript)
    └── student.onnx       (ONNX)
```

Example metadata.json structure:
```json
{
  "model_type": "SpikingStudentLM",
  "architecture_version": "v1.0",
  "vocab_size": 50257,
  "student_params": 123456,
  "architecture": {
    "dim": 128,
    "depth": 2,
    "num_heads": 4
  },
  "snn_config": {
    "num_timesteps": 8,
    "surrogate_type": "fast_sigmoid",
    "spike_threshold": 0.5
  },
  "training_config": {
    "num_steps": 10000,
    "batch_size": 4,
    "grad_accum_steps": 8,
    "teacher_model": "meta-llama/Llama-3.2-3B",
    "lr": 0.0003,
    "scheduler": "cosine",
    "warmup_steps": 500,
    "temperature": 1.0,
    "dataset": "wikitext-2",
    "max_length": 512
  },
  "training_results": {
    "steps": 10000,
    "avg_loss": 2.345
  },
  "metadata": {
    "timestamp": "2024-12-08T11:46:46.042Z",
    "git_commit": "4756416a"
  },
  "exports": [
    {
      "format": "torchscript",
      "path": "artifacts/snn_student_llama/exports/student_mobile.pt",
      "timestamp": "2024-12-08T12:30:15.123Z",
      "file_size_bytes": 1048576
    }
  ]
}
```

## Consuming artifacts with `SNNLLMBackend`
`src/llm_snn_backend.py` provides a backend that loads the student artifacts and exposes the same interface as other LLM backends.

### Loading behavior
- Paths: It looks for `student.pt` and `metadata.json` at construction time (defaults: `artifacts/snn_student/student.pt` and `artifacts/snn_student/metadata.json`). You can point it to your run with `SNNLLMBackend(model_path="artifacts/snn_student_llama/student.pt")` and optionally `metadata_path` if you saved elsewhere.
- Metadata: The backend parses `metadata.json` to recover the stored `config`, `snn_config`, and tokenizer hints. If the file is missing or malformed, it proceeds with empty defaults while logging a warning.
- Tokenizer: It prefers the tokenizer named in metadata (`config["tokenizer_name"]`) or a user override; falls back to GPT-2. If transformers are unavailable, it falls back to a whitespace tokenizer stub.
- Model loading: Tries TorchScript via `torch.jit.load`; if that fails, it attempts `torch.load` to retrieve a state dict. Missing or un-loadable artifacts trigger a stubbed path that still returns deterministic text so demos keep running.

### Minimal generation example
Once your artifacts exist, instantiate the backend and generate:

```python
from src.llm_snn_backend import SNNLLMBackend

backend = SNNLLMBackend(
    model_path="artifacts/snn_student_llama/student.pt",
    metadata_path="artifacts/snn_student_llama/metadata.json",
)
print(backend.generate("Hello from the glasses", max_tokens=24))
```

If the artifacts or PyTorch are unavailable, the backend emits warnings and uses a stubbed tokenizer/model so the call still succeeds—useful for quick demos or CI environments.

## Architecture considerations for larger teachers

The current `SpikingStudentLM` architecture is designed for demonstrations with small teachers like tiny-gpt2. When distilling from larger teachers (Llama-3.2-3B, Qwen-2.5-3B), consider these improvements:

### Student architecture scaling
- **Increase capacity**: Scale up `dim` (e.g., 256-512) and `depth` (e.g., 4-8 layers) for better knowledge capture.
- **Position embeddings**: Add learned or RoPE (Rotary Position Embeddings) for longer sequences.
- **Efficient attention**: Implement grouped query attention or sparse attention patterns.
- **Quantization**: Consider quantization-aware training for INT8 deployment to meet power constraints (<100mW).
- **Gradient checkpointing**: Use gradient checkpointing for memory-efficient training with deeper models.

### Training considerations
- **Longer sequences**: Use `--max-length 512-1024` to match teacher capabilities.
- **Effective batch size**: Maintain effective batch size (batch_size × grad_accum_steps) of 32-64.
- **Learning rate schedule**: Use cosine or linear scheduling with warmup for stable convergence.
- **SNN timesteps**: Increase to 8-16 for better temporal dynamics.
- **Surrogate gradients**: Experiment with `fast_sigmoid` or `arctan` for improved gradient flow.

### Resource requirements
- **GPU memory**: 16GB+ VRAM for 3B teachers with batch_size 2-4.
- **Training time**: 10000+ steps recommended for production quality (several hours on single GPU).
- **Storage**: ~1GB for teacher model cache, ~10MB for student artifacts.

See the TODO comments in `scripts/train_snn_student.py` for specific architecture improvement suggestions.

## Exporting for mobile deployment

The training script supports exporting trained models for mobile deployment using `--export-format`:

### TorchScript Export (PyTorch Mobile)

TorchScript provides seamless integration with PyTorch Mobile runtime on Android/iOS:

```bash
# During training
python scripts/train_snn_student.py \
  --teacher-model meta-llama/Llama-3.2-3B \
  --dataset wikitext-2 \
  --num-steps 10000 \
  --export-format torchscript \
  --output-dir artifacts/snn_student_llama

# Or export separately using src/snn_export.py
python -c "
from src.snn_export import load_and_export
load_and_export('artifacts/snn_student_llama', export_formats=['torchscript'])
"
```

**Mobile Integration:**

Android (Java):
```java
// Load TorchScript model
Module module = LiteModuleLoader.load("student_mobile.pt");

// Prepare input (tokenized text)
long[] inputIds = {101, 2054, 2003, 102};
Tensor inputTensor = Tensor.fromBlob(inputIds, new long[]{1, 4});

// Run inference
IValue output = module.forward(IValue.from(inputTensor));
Tensor logits = output.toTensor();  // [1, 4, vocab_size]
```

iOS (Swift):
```swift
// Load TorchScript model
guard let module = try? TorchModule(fileAtPath: modelPath) else { return }

// Prepare input
let inputIds: [Int64] = [101, 2054, 2003, 102]
let inputTensor = Tensor(shape: [1, 4], data: inputIds)

// Run inference
guard let outputTensor = module.forward(inputTensor) else { return }
```

### ONNX Export (Cross-Platform)

ONNX provides broader runtime support including ONNX Runtime Mobile, TensorFlow Lite, and CoreML:

```bash
# During training
python scripts/train_snn_student.py \
  --teacher-model meta-llama/Llama-3.2-3B \
  --dataset wikitext-2 \
  --num-steps 10000 \
  --export-format onnx \
  --output-dir artifacts/snn_student_llama

# Or export separately
python -c "
from src.snn_export import load_and_export
load_and_export('artifacts/snn_student_llama', export_formats=['onnx'])
"
```

**Mobile Integration:**

Android (ONNX Runtime):
```java
// Load ONNX model
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
// Load ONNX model
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

### Export Configuration

The export utilities (`src/snn_export.py`) provide comprehensive validation and error handling:

- **Shape validation**: Ensures input tensors have correct shape [batch, seq_len]
- **Vocabulary validation**: Checks tokens are within valid range [0, vocab_size)
- **SNN-specific handling**: Documents timestep dimensions and stateful layer considerations
- **Defensive errors**: Meaningful error messages for common issues

Example programmatic export:
```python
from src.snn_export import export_to_torchscript, export_to_onnx
import torch

# Create example inputs
example_inputs = {"input_ids": torch.zeros((1, 4), dtype=torch.long)}

# Export TorchScript
export_to_torchscript(
    output_path="artifacts/snn_student/exports/student_mobile.pt",
    example_inputs=example_inputs
)

# Export ONNX
export_to_onnx(
    output_path="artifacts/snn_student/exports/student.onnx",
    example_inputs=example_inputs
)
```

### Legacy ONNX Export

The old `--export-onnx` flag and `scripts/export_snn_to_onnx.py` are deprecated but still work for backward compatibility:

```bash
# Deprecated (still works)
python scripts/train_snn_student.py --export-onnx ...

# Preferred
python scripts/train_snn_student.py --export-format onnx ...
```

## Mobile deployment considerations

### Tokenizer Compatibility
- Package `student.onnx` or `student_mobile.pt` with your mobile client (e.g., copy into Android assets or an iOS bundle).
- Reuse the tokenizer configuration from `metadata.json` to ensure the mobile client tokenizes text identically to training.
- The same vocab size is embedded in the exported models, so tokenizer/token-to-id parity is required for correct logits.

### Performance Optimization
- For on-device deployment, consider using quantized models (INT8) to meet the <100mW power target and <50ms latency requirements.
- Use batch size of 1 for mobile inference to minimize memory usage.
- Pre-tokenize inputs on device to match training tokenizer vocab_size.

### SNN-Specific Considerations

1. **Timesteps Dimension**: Current SNN implementation processes sequence-level spikes without explicit timestep dimension. Models operate on [batch, seq_len] inputs, producing [batch, seq_len, vocab_size] outputs.

2. **Stateful Layers**: SpikingActivation uses surrogate gradients (sigmoid, fast_sigmoid, triangular, arctan) which are stateless during inference - no hidden state reset needed between sequences.

3. **Mobile Optimization**: Exported models are in eval mode to remove training-only operations. Consider quantization-aware training for INT8 deployment.

4. **Performance Targets**:
   - Latency: <50ms per inference on mobile devices
   - Power: <100mW during active inference
   - Model size: <5MB (student only, compressed)

## Best practices

### Reproducibility
- Git commit hash: The script automatically tracks the current git commit in `metadata.json` (disable with `--no-git-tracking`).
- Timestamp: All training runs include ISO 8601 timestamps for tracking.
- Full config: Complete CLI arguments are saved in metadata for exact reproduction.

### Hyperparameter tuning
- Start with demo config: Validate pipeline with tiny-gpt2 before scaling up.
- Tune learning rate: Use 1e-4 for small runs, 3e-4 for large runs.
- Adjust temperature: Higher temperature (2.0-4.0) for softer targets, 1.0 for direct distillation.
- SNN threshold: Tune between 0.5-1.5 based on validation performance.

### Monitoring
- Loss logs: Watch for steady decrease; increase num_steps if still declining.
- Learning rate: Monitor LR in logs (printed with loss when scheduler is active).
- GPU memory: Reduce batch_size if OOM, increase grad_accum_steps to maintain effective batch size.
