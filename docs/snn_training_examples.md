# SNN Student Training Examples

This document provides practical examples for training SNN student models using `scripts/train_snn_student.py` with different teacher models and configurations.

## Table of Contents
- [Demo: Tiny Teacher (Colab-Friendly)](#demo-tiny-teacher-colab-friendly)
- [Production: Llama-3.2-3B Teacher](#production-llama-32-3b-teacher)
- [Production: Qwen-2.5-3B Teacher](#production-qwen-25-3b-teacher)
- [Advanced: Custom SNN Configuration](#advanced-custom-snn-configuration)
- [Advanced: Learning Rate Scheduling](#advanced-learning-rate-scheduling)

## Demo: Tiny Teacher (Colab-Friendly)

Perfect for quick testing, debugging, and demonstration purposes. Uses a tiny GPT-2 teacher with minimal compute requirements.

```bash
# Basic demo with synthetic data (runs in ~1 minute on CPU)
python scripts/train_snn_student.py \
  --teacher-model sshleifer/tiny-gpt2 \
  --dataset synthetic \
  --num-steps 50 \
  --batch-size 4 \
  --grad-accum-steps 2 \
  --output-dir artifacts/snn_student_demo

# Demo with real dataset (wikitext-2)
python scripts/train_snn_student.py \
  --teacher-model sshleifer/tiny-gpt2 \
  --dataset wikitext-2 \
  --num-steps 100 \
  --batch-size 2 \
  --grad-accum-steps 4 \
  --max-length 128 \
  --output-dir artifacts/snn_student_demo_wikitext
```

**Expected results:**
- Training time: ~1-2 minutes on CPU
- Model size: ~500KB
- Artifacts: `student.pt`, `metadata.json`

## Production: Llama-3.2-3B Teacher

For production-quality distillation from Meta's Llama-3.2-3B model. Requires GPU with 16GB+ VRAM.

### Basic Configuration

```bash
python scripts/train_snn_student.py \
  --teacher-model meta-llama/Llama-3.2-3B \
  --dataset wikitext-2 \
  --num-steps 10000 \
  --batch-size 4 \
  --grad-accum-steps 8 \
  --max-length 512 \
  --lr 3e-4 \
  --output-dir artifacts/snn_student_llama
```

### With Cosine Annealing Schedule

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
  --output-dir artifacts/snn_student_llama_cosine
```

### With Custom SNN Parameters

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
  --output-dir artifacts/snn_student_llama_optimized
```

### With ONNX Export

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
  --export-onnx \
  --output-dir artifacts/snn_student_llama_onnx
```

**Expected results:**
- Training time: ~4-6 hours on A100 GPU
- Model size: ~1-2MB (student only)
- Effective batch size: 32 (4 × 8)
- Artifacts: `student.pt`, `metadata.json`, `student.onnx` (if --export-onnx)

## Production: Qwen-2.5-3B Teacher

For distillation from Alibaba's Qwen-2.5-3B model. Requires GPU with 16GB+ VRAM.

### Basic Configuration with Longer Context

```bash
python scripts/train_snn_student.py \
  --teacher-model Qwen/Qwen2.5-3B \
  --dataset wikitext-2 \
  --num-steps 10000 \
  --batch-size 2 \
  --grad-accum-steps 16 \
  --max-length 1024 \
  --lr 3e-4 \
  --output-dir artifacts/snn_student_qwen
```

### With Linear Schedule and Longer Warmup

```bash
python scripts/train_snn_student.py \
  --teacher-model Qwen/Qwen2.5-3B \
  --dataset wikitext-2 \
  --num-steps 10000 \
  --batch-size 2 \
  --grad-accum-steps 16 \
  --max-length 1024 \
  --lr 3e-4 \
  --scheduler linear \
  --warmup-steps 1000 \
  --output-dir artifacts/snn_student_qwen_linear
```

### Optimized for Long Context

```bash
python scripts/train_snn_student.py \
  --teacher-model Qwen/Qwen2.5-3B \
  --dataset wikitext-2 \
  --num-steps 15000 \
  --batch-size 2 \
  --grad-accum-steps 16 \
  --max-length 2048 \
  --lr 2e-4 \
  --scheduler linear \
  --warmup-steps 1500 \
  --snn-timesteps 16 \
  --snn-surrogate arctan \
  --snn-threshold 0.7 \
  --temperature 2.0 \
  --output-dir artifacts/snn_student_qwen_longctx
```

**Expected results:**
- Training time: ~6-10 hours on A100 GPU
- Model size: ~1-2MB (student only)
- Effective batch size: 32 (2 × 16)
- Context length: Up to 2048 tokens

## Advanced: Custom SNN Configuration

### Testing Different Surrogate Gradients

#### Sigmoid (Default - Smooth and Stable)
```bash
python scripts/train_snn_student.py \
  --teacher-model sshleifer/tiny-gpt2 \
  --dataset synthetic \
  --num-steps 100 \
  --snn-surrogate sigmoid \
  --output-dir artifacts/snn_surrogate_sigmoid
```

#### Fast Sigmoid (Faster Computation)
```bash
python scripts/train_snn_student.py \
  --teacher-model sshleifer/tiny-gpt2 \
  --dataset synthetic \
  --num-steps 100 \
  --snn-surrogate fast_sigmoid \
  --output-dir artifacts/snn_surrogate_fast_sigmoid
```

#### Triangular (Piecewise Linear)
```bash
python scripts/train_snn_student.py \
  --teacher-model sshleifer/tiny-gpt2 \
  --dataset synthetic \
  --num-steps 100 \
  --snn-surrogate triangular \
  --output-dir artifacts/snn_surrogate_triangular
```

#### Arctan (Smooth Alternative)
```bash
python scripts/train_snn_student.py \
  --teacher-model sshleifer/tiny-gpt2 \
  --dataset synthetic \
  --num-steps 100 \
  --snn-surrogate arctan \
  --output-dir artifacts/snn_surrogate_arctan
```

### Tuning Spike Threshold

```bash
# Lower threshold (more spikes)
python scripts/train_snn_student.py \
  --teacher-model sshleifer/tiny-gpt2 \
  --dataset synthetic \
  --num-steps 100 \
  --snn-threshold 0.5 \
  --output-dir artifacts/snn_threshold_05

# Higher threshold (fewer spikes)
python scripts/train_snn_student.py \
  --teacher-model sshleifer/tiny-gpt2 \
  --dataset synthetic \
  --num-steps 100 \
  --snn-threshold 1.5 \
  --output-dir artifacts/snn_threshold_15
```

### Adjusting Timesteps

```bash
# Minimal timesteps (faster)
python scripts/train_snn_student.py \
  --teacher-model sshleifer/tiny-gpt2 \
  --dataset synthetic \
  --num-steps 100 \
  --snn-timesteps 2 \
  --output-dir artifacts/snn_timesteps_2

# More timesteps (better temporal dynamics)
python scripts/train_snn_student.py \
  --teacher-model sshleifer/tiny-gpt2 \
  --dataset synthetic \
  --num-steps 100 \
  --snn-timesteps 16 \
  --output-dir artifacts/snn_timesteps_16
```

## Advanced: Learning Rate Scheduling

### Constant (No Schedule - Default)
```bash
python scripts/train_snn_student.py \
  --teacher-model sshleifer/tiny-gpt2 \
  --dataset synthetic \
  --num-steps 100 \
  --lr 1e-4 \
  --scheduler constant \
  --output-dir artifacts/scheduler_constant
```

### Cosine Annealing (Smooth Decay)
```bash
python scripts/train_snn_student.py \
  --teacher-model sshleifer/tiny-gpt2 \
  --dataset synthetic \
  --num-steps 100 \
  --lr 1e-4 \
  --scheduler cosine \
  --output-dir artifacts/scheduler_cosine
```

### Cosine with Warmup (Recommended for Large Runs)
```bash
python scripts/train_snn_student.py \
  --teacher-model meta-llama/Llama-3.2-3B \
  --dataset wikitext-2 \
  --num-steps 10000 \
  --lr 3e-4 \
  --scheduler cosine \
  --warmup-steps 500 \
  --output-dir artifacts/scheduler_cosine_warmup
```

### Linear Decay (Gradual Reduction)
```bash
python scripts/train_snn_student.py \
  --teacher-model sshleifer/tiny-gpt2 \
  --dataset synthetic \
  --num-steps 100 \
  --lr 1e-4 \
  --scheduler linear \
  --output-dir artifacts/scheduler_linear
```

### Linear with Extended Warmup
```bash
python scripts/train_snn_student.py \
  --teacher-model Qwen/Qwen2.5-3B \
  --dataset wikitext-2 \
  --num-steps 10000 \
  --lr 3e-4 \
  --scheduler linear \
  --warmup-steps 1000 \
  --output-dir artifacts/scheduler_linear_warmup
```

## Metadata Tracking

All training runs automatically track:
- Git commit hash (use `--no-git-tracking` to disable)
- Training timestamp
- Complete hyperparameters
- Architecture details
- Training results (steps, loss)

Example metadata inspection:
```bash
# After training
cat artifacts/snn_student_llama/metadata.json | jq .

# Check git commit
cat artifacts/snn_student_llama/metadata.json | jq .metadata.git_commit

# Check SNN config
cat artifacts/snn_student_llama/metadata.json | jq .snn_config
```

## Troubleshooting

### Out of Memory (OOM)
Reduce `--batch-size` and increase `--grad-accum-steps` to maintain effective batch size:
```bash
# Instead of: --batch-size 4 --grad-accum-steps 8
# Use:        --batch-size 2 --grad-accum-steps 16
```

### Training Too Slow
- Use GPU: Remove `--device cpu` (auto-detects CUDA)
- Reduce sequence length: `--max-length 256` instead of 512
- Reduce timesteps: `--snn-timesteps 4` instead of 8
- Use faster surrogate: `--snn-surrogate fast_sigmoid`

### Loss Not Decreasing
- Increase learning rate: `--lr 3e-4` or `5e-4`
- Add warmup: `--warmup-steps 500`
- Increase temperature: `--temperature 2.0` for softer targets
- Check dataset: Try `--dataset wikitext-2` instead of synthetic

### Model Performance Issues
- Increase training steps: `--num-steps 10000` or more
- Use larger effective batch: Increase `--grad-accum-steps`
- Tune SNN threshold: Try values between 0.5 and 1.5
- Experiment with surrogate gradients: Try different `--snn-surrogate` options

## Resource Requirements

| Configuration | GPU Memory | Training Time | Model Size |
|--------------|------------|---------------|------------|
| Demo (tiny-gpt2) | None (CPU) | 1-2 min | ~500KB |
| Llama-3.2-3B | 16GB+ | 4-6 hours | ~1-2MB |
| Qwen-2.5-3B (1024) | 16GB+ | 6-8 hours | ~1-2MB |
| Qwen-2.5-3B (2048) | 24GB+ | 8-12 hours | ~1-2MB |

Note: Training time estimates are for A100 GPU. Student model size is for the compressed student only, not including teacher cache.
