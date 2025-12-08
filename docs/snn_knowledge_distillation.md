# SNN Knowledge Distillation for SmartGlass-AI-Agent

This document describes the Spiking Neural Network (SNN) knowledge distillation system for deploying AI models on smart glasses hardware with minimal power consumption.

## Overview

Knowledge distillation transfers knowledge from a large "teacher" model (e.g., GPT-2, Llama) to a smaller, more efficient "student" model based on Spiking Neural Networks (SNNs). This enables on-device inference with:

- **Ultra-low power consumption**: <100mW typical
- **Fast inference**: <50ms latency
- **Small memory footprint**: <10MB models
- **Neuromorphic hardware compatibility**: Ready for specialized SNN chips

## Why SNNs for Smart Glasses?

Traditional neural networks (ANNs) continuously process floating-point operations, consuming significant power. SNNs communicate via discrete spikes (like biological neurons), offering:

1. **Event-driven computation**: Only active neurons consume power
2. **Temporal dynamics**: Natural processing of time-series data (audio, video)
3. **Hardware efficiency**: Optimized for neuromorphic chips (Intel Loihi, IBM TrueNorth)
4. **Low latency**: Minimal computation between spikes

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Teacher Model (Pre-trained Transformer)                    │
│  - GPT-2 / Llama-3.2-3B / Qwen-2.5-3B                      │
│  - Full precision (FP32)                                    │
│  - Large parameters (~125M - 3B)                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Knowledge Transfer
                     │ (Soft Labels + KD Loss)
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Student Model (Spiking Neural Network)                     │
│  - Spiking Transformer Architecture                         │
│  - 4 layers × 256 hidden × 4 heads                         │
│  - ~5M parameters                                           │
│  - INT8 quantized                                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Export for Deployment
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Deployment Formats                                         │
│  - PyTorch (.pt)                                           │
│  - ONNX (.onnx)                                            │
│  - TensorFlow Lite (.tflite)                               │
└─────────────────────────────────────────────────────────────┘
```

## Distillation Process

### 1. Configuration

Create a distillation configuration:

```python
from src.snn_knowledge_distillation import SNNDistillationConfig

config = SNNDistillationConfig(
    # Teacher model
    teacher_model="gpt2",
    teacher_checkpoint=None,  # Use default pretrained
    
    # Student architecture
    student_architecture="spiking_transformer",
    student_hidden_size=256,
    student_num_layers=4,
    student_num_heads=4,
    
    # Distillation parameters
    temperature=2.0,          # Softens probability distributions
    alpha_ce=0.5,            # Cross-entropy loss weight
    alpha_kd=0.5,            # Knowledge distillation loss weight
    
    # Training
    learning_rate=5e-4,
    batch_size=8,
    num_epochs=10,
    gradient_accumulation_steps=4,
    
    # SNN parameters
    spiking_threshold=1.0,
    membrane_decay=0.9,
    timesteps=10,
    
    # Hardware targets
    target_latency_ms=50.0,
    target_power_mw=100.0,
    quantization_bits=8,
    
    # Output
    output_dir="artifacts/snn_student",
    export_onnx=True,
)

# Save configuration
config.save("config/snn_distillation.json")
```

### 2. Training (Using Existing Script)

The actual training is performed using the `scripts/train_snn_student.py` script:

```bash
python scripts/train_snn_student.py \
    --teacher-model gpt2 \
    --num-steps 1000 \
    --batch-size 8 \
    --grad-accum-steps 4 \
    --lr 5e-4 \
    --temperature 2.0 \
    --output-dir artifacts/snn_student \
    --export-onnx
```

Training outputs:
- `artifacts/snn_student/student.pt` - PyTorch student model
- `artifacts/snn_student/metadata.json` - Model metadata
- `artifacts/snn_student/student.onnx` - ONNX export (if --export-onnx)

### 3. Using the Placeholder Interface

For configuration and planning purposes, use the placeholder interface:

```python
from src.snn_knowledge_distillation import (
    SNNDistillationTrainer,
    create_default_config,
)

# Create default configuration
config = create_default_config()

# Initialize trainer (placeholder)
trainer = SNNDistillationTrainer(config)

# These are placeholders - actual training uses scripts/train_snn_student.py
trainer.load_teacher()           # Logs placeholder message
trainer.initialize_student()     # Logs placeholder message
results = trainer.train()        # Returns placeholder results

print(results)
# {
#   "status": "placeholder",
#   "message": "Use scripts/train_snn_student.py for training",
#   "config": {...},
#   "expected_output": "artifacts/snn_student/student.pt"
# }
```

## SNN Architecture Details

### Spiking Transformer

The student model uses a Spiking Transformer architecture:

```
Input Tokens → Token Embedding
             ↓
    ┌────────────────────┐
    │  Spiking Layer 1   │
    │  - Multi-head      │
    │    Attention       │
    │  - LIF Neurons     │
    │  - Membrane Decay  │
    └──────┬─────────────┘
           ↓
    ┌────────────────────┐
    │  Spiking Layer 2   │
    └──────┬─────────────┘
           ↓
    ┌────────────────────┐
    │  Spiking Layer 3   │
    └──────┬─────────────┘
           ↓
    ┌────────────────────┐
    │  Spiking Layer 4   │
    └──────┬─────────────┘
           ↓
    Output Projection → Logits
```

### Leaky Integrate-and-Fire (LIF) Neurons

Each neuron follows LIF dynamics:

```
Membrane potential: V(t+1) = β·V(t) + I(t)
Spike output: S(t) = 1 if V(t) ≥ θ, else 0
Reset: V(t) = 0 if S(t) = 1

Where:
- β: membrane decay (0.9 typical)
- θ: firing threshold (1.0 typical)
- I(t): input current at time t
- S(t): spike output at time t
```

### Surrogate Gradient

Since spike function is non-differentiable, we use surrogate gradients for backpropagation:

```
Forward: spike = Heaviside(V - θ)
Backward: ∂spike/∂V ≈ 1/(1 + β|V - θ|)

Where β controls steepness (10.0 typical)
```

## Knowledge Distillation Loss

The training objective combines two losses:

### Cross-Entropy Loss (Hard Labels)
```
L_CE = -Σ y_true · log(y_pred)
```

### Knowledge Distillation Loss (Soft Labels)
```
L_KD = T² · KL(softmax(z_student/T) || softmax(z_teacher/T))

Where:
- T: temperature (2.0 typical)
- z: logits from model
- KL: Kullback-Leibler divergence
```

### Combined Loss
```
L_total = α · L_CE + (1-α) · L_KD

Where α = 0.5 (balanced default)
```

## Hardware Profiling (Placeholder)

The `SNNHardwareProfiler` provides placeholder interfaces for measuring performance:

```python
from src.snn_knowledge_distillation import SNNHardwareProfiler

profiler = SNNHardwareProfiler("artifacts/snn_student/student.pt")

# Profile latency (placeholder)
latency = profiler.profile_latency()
print(f"Mean latency: {latency['mean_ms']:.1f}ms")
print(f"P95 latency: {latency['p95_ms']:.1f}ms")

# Profile power consumption (placeholder)
power = profiler.profile_power()
print(f"Mean power: {power['mean_mw']:.1f}mW")
print(f"Peak power: {power['peak_mw']:.1f}mW")

# Profile accuracy (placeholder)
accuracy = profiler.profile_accuracy(test_data)
print(f"Accuracy: {accuracy['accuracy']:.2%}")
```

**Note:** These are placeholder interfaces. Actual hardware profiling requires:
- Target hardware (neuromorphic chip or edge processor)
- Power measurement tools
- Profiling instrumentation

## Integration with SmartGlassAgent

Use the distilled SNN model with SmartGlassAgent:

```python
from src.smartglass_agent import SmartGlassAgent
from src.llm_snn_backend import SNNLLMBackend

# Load SNN student model
snn_backend = SNNLLMBackend(
    model_path="artifacts/snn_student/student.pt"
)

# Initialize agent with SNN backend
agent = SmartGlassAgent(
    whisper_model="base",
    clip_model="openai/clip-vit-base-patch32",
    llm_backend=snn_backend,
    provider="meta"
)

# Process queries with on-device SNN inference
result = agent.process_multimodal_query(
    text_query="What do you see?",
    image_input="path/to/image.jpg"
)

print(result["response"])
```

## Performance Targets

### Latency
- **Target**: <50ms per inference
- **Actual** (placeholder): ~50ms
- **Breakdown**:
  - Tokenization: ~5ms
  - SNN forward pass: ~40ms
  - Decoding: ~5ms

### Power Consumption
- **Target**: <100mW average
- **Actual** (placeholder): ~100mW
- **Comparison**:
  - GPT-2 full (GPU): ~10W
  - GPT-2 mobile (CPU): ~500mW
  - SNN student: ~100mW ✓

### Model Size
- **Teacher (GPT-2)**: ~500MB (125M params)
- **Student (SNN)**: ~5MB (5M params, INT8)
- **Compression ratio**: 100x

### Accuracy
- **Teacher perplexity**: ~18.0
- **Student perplexity (target)**: ~25.0
- **Accuracy retention**: >85%

## Training Tips

### Dataset Selection
```python
# Good datasets for smart glasses domain:
datasets = [
    "wikitext-2",           # General language
    "openwebtext",          # Web text
    "cc_news",              # News articles
    "custom_glasses_data",  # Domain-specific
]
```

### Hyperparameter Tuning

**Temperature** (controls soft label smoothness):
- Low (1.0-1.5): Preserve teacher confidence
- Medium (2.0-3.0): Balance exploration ✓
- High (4.0+): Over-smoothed, loss of information

**Alpha** (balance CE and KD loss):
- 0.0: Only KD loss (risky)
- 0.5: Balanced ✓
- 1.0: Only CE loss (ignores teacher)

**Learning Rate**:
- Too low (<1e-5): Slow convergence
- Optimal (5e-4): Good balance ✓
- Too high (>1e-3): Unstable training

### Gradient Accumulation

For limited memory:
```python
effective_batch_size = batch_size * gradient_accumulation_steps
# Example: 8 * 4 = 32 effective batch size
```

## Neuromorphic Hardware

### Intel Loihi 2
- Event-driven SNN processor
- 1M neurons per chip
- <100mW power budget
- Asynchronous spike communication

### IBM TrueNorth
- 1M neurons, 256M synapses
- 70mW power consumption
- 48 chips scalable
- No floating-point operations

### Deployment Steps
1. Export model to ONNX
2. Convert to neuromorphic format
3. Map to chip architecture
4. Validate accuracy on hardware
5. Profile power/latency

## Future Enhancements

### Short-term (Placeholder)
- [ ] Implement actual hardware profiling
- [ ] Add multi-timestep optimization
- [ ] Support for various SNN architectures
- [ ] Automated hyperparameter search
- [ ] Online distillation during deployment

### Long-term
- [ ] Continuous learning on-device
- [ ] Adaptive timesteps based on input
- [ ] Mixed-precision training
- [ ] Federated distillation across devices
- [ ] Custom neuromorphic chip support

## Troubleshooting

### Issue: Student model not learning

**Solutions:**
- Check temperature (try 2.0-3.0)
- Increase number of timesteps
- Adjust learning rate
- Verify teacher model is loaded correctly

### Issue: High power consumption

**Solutions:**
- Reduce number of active neurons
- Increase membrane decay
- Use sparser activations
- Apply pruning post-training

### Issue: Poor accuracy on edge cases

**Solutions:**
- Add domain-specific data to training
- Use intermediate distillation
- Ensemble multiple students
- Fine-tune on target distribution

## References

### Papers
- Hinton et al. "Distilling the Knowledge in a Neural Network" (2015)
- Maass, W. "Networks of Spiking Neurons" (1997)
- Diehl & Cook "Unsupervised Learning of Digit Recognition" (2015)

### Related Documentation
- [SNN Pipeline](snn_pipeline.md)
- [LLM Backends](README_MODEL_CHOICES.md)
- [Training Script](../scripts/train_snn_student.py)

## Current Status

⚠️ **Placeholder Implementation**: The `src/snn_knowledge_distillation.py` module provides placeholder interfaces for configuration and planning. Actual training should use `scripts/train_snn_student.py`.

**Available:**
- ✅ Configuration management
- ✅ Interface definitions
- ✅ Training script (`scripts/train_snn_student.py`)
- ✅ SNN backend runtime (`src/llm_snn_backend.py`)

**Placeholder:**
- ⚠️ Hardware profiling
- ⚠️ Neuromorphic deployment
- ⚠️ Online distillation
- ⚠️ Advanced optimizations

## Support

For questions about SNN knowledge distillation:
- GitHub Issues: https://github.com/farmountain/SmartGlass-AI-Agent/issues
- Training Script: `scripts/train_snn_student.py`
- Backend Implementation: `src/llm_snn_backend.py`
