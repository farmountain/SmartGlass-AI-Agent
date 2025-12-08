"""Training script for a lightweight spiking student model with KD.

This script provides a minimal pipeline for distilling a teacher language
model into a small spiking-friendly student. It is designed to be easy to run
in constrained environments (e.g., Google Colab) with configurable batch sizes
and gradient accumulation.

Supports larger teachers like Llama-3.2-3B and Qwen-2.5-3B with configurable
SNN hyperparameters, learning rate schedules, and comprehensive metadata tracking.

Example usage:
  # Demo with tiny teacher (Colab-friendly)
  python scripts/train_snn_student.py \\
    --teacher-model sshleifer/tiny-gpt2 \\
    --dataset synthetic \\
    --num-steps 50

  # Production training with Llama-3.2-3B
  python scripts/train_snn_student.py \\
    --teacher-model meta-llama/Llama-3.2-3B \\
    --dataset wikitext-2 \\
    --num-steps 10000 \\
    --batch-size 4 \\
    --grad-accum-steps 8 \\
    --max-length 512 \\
    --lr 3e-4 \\
    --scheduler cosine \\
    --warmup-steps 500 \\
    --snn-timesteps 8 \\
    --snn-surrogate fast_sigmoid \\
    --snn-threshold 0.5
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

import torch
from torch import nn
from torch.nn import functional as F


@dataclass
class SNNConfig:
    """Configuration for SNN-specific hyperparameters.
    
    These parameters control the spiking neuron behavior and training dynamics.
    """
    num_timesteps: int = 4  # Number of simulation timesteps for spiking neurons
    surrogate_type: str = "sigmoid"  # Surrogate gradient: sigmoid, fast_sigmoid, triangular, arctan
    spike_threshold: float = 1.0  # Threshold for spike generation
    
    def __post_init__(self):
        valid_surrogates = {"sigmoid", "fast_sigmoid", "triangular", "arctan"}
        if self.surrogate_type not in valid_surrogates:
            raise ValueError(f"surrogate_type must be one of {valid_surrogates}, got {self.surrogate_type}")


@dataclass
class TrainConfig:
    """Main training configuration."""
    teacher_model: str
    dataset: str
    dataset_path: Optional[str]
    output_dir: str
    lr: float
    batch_size: int
    grad_accum_steps: int
    num_steps: int
    log_interval: int
    device: str
    max_length: int
    temperature: float
    export_onnx: bool
    
    # Learning rate schedule
    scheduler: str = "constant"  # constant, cosine, linear
    warmup_steps: int = 0
    
    # SNN-specific configuration
    snn_config: SNNConfig = field(default_factory=SNNConfig)
    
    # Metadata tracking
    track_git_commit: bool = True


# ------------------------ Teacher utilities ------------------------


def load_teacher_model(model_name: str, device: str):
    """Lazily import and load a teacher model with clear guidance.

    The import is intentionally placed inside the function to keep the module
    importable even when ``transformers`` is unavailable; a descriptive error
    is raised instead of a cryptic ``ModuleNotFoundError``.
    """

    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover - runtime guard
        raise ModuleNotFoundError(
            "The 'transformers' package is required for teacher loading. "
            "Install it with `pip install transformers` or use a prepared "
            "checkpoint path."
        ) from exc

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name)
    model.to(device)
    model.eval()
    return model, tokenizer


# ------------------------ Dataset helpers ------------------------


def load_prompts(dataset: str, dataset_path: Optional[str]) -> List[str]:
    """Load prompts from a dataset name, file path, or fall back to synthetic samples."""

    if dataset_path:
        path = Path(dataset_path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset path {dataset_path} does not exist")
        return [line.strip() for line in path.read_text().splitlines() if line.strip()]

    if dataset.lower() == "synthetic":
        return [
            "Describe a sunrise over the mountains.",
            "List three safety tips for biking in the city.",
            "Write a short haiku about technology.",
            "Explain knowledge distillation in simple terms.",
            "Suggest a healthy lunch recipe with avocado.",
        ]

    try:
        from datasets import load_dataset  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover - runtime guard
        raise ModuleNotFoundError(
            "The 'datasets' package is required for loading the requested dataset. "
            "Install it with `pip install datasets` or use `--dataset synthetic` or `--dataset-path`."
        ) from exc

    dataset_id = dataset
    dataset_kwargs = {}
    if dataset.lower() in {"wikitext-2", "wikitext-2-raw"}:
        dataset_id = "wikitext"
        dataset_kwargs["name"] = "wikitext-2-raw-v1"

    prompts_ds = load_dataset(dataset_id, split="train", **dataset_kwargs)
    text_column = "text" if "text" in prompts_ds.column_names else prompts_ds.column_names[0]
    prompts = [str(sample).strip() for sample in prompts_ds[text_column] if str(sample).strip()]
    if not prompts:
        raise ValueError(f"No prompts found in dataset '{dataset}'.")
    return prompts


# ------------------------ Student model ------------------------


class SpikingActivation(nn.Module):
    """Approximate spiking activation with configurable surrogate gradient.
    
    Supports multiple surrogate gradient functions for training SNNs:
    - sigmoid: Smooth sigmoid derivative (default)
    - fast_sigmoid: Faster approximation with limited range
    - triangular: Piecewise linear triangle function
    - arctan: Arctan-based smooth function
    """

    def __init__(self, threshold: float = 1.0, surrogate_type: str = "sigmoid"):
        super().__init__()
        self.threshold = threshold
        self.surrogate_type = surrogate_type

    def _surrogate_gradient(self, x: torch.Tensor) -> torch.Tensor:
        """Compute surrogate gradient for backward pass."""
        if self.surrogate_type == "sigmoid":
            return torch.sigmoid(x)
        elif self.surrogate_type == "fast_sigmoid":
            # Fast sigmoid with limited range
            return 1 / (1 + torch.abs(x))
        elif self.surrogate_type == "triangular":
            # Triangular surrogate: max(0, 1 - |x|)
            return torch.clamp(1 - torch.abs(x), min=0)
        elif self.surrogate_type == "arctan":
            # Arctan-based smooth function
            return 1 / (1 + (math.pi * x / 2) ** 2)
        else:
            # Fallback to sigmoid
            return torch.sigmoid(x)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Straight-through estimator for spike generation.
        out = (x > self.threshold).float()
        # Apply surrogate gradient for smooth backprop.
        shifted = x - self.threshold
        return out + self._surrogate_gradient(shifted) - self._surrogate_gradient(shifted).detach()


class SpikingSelfAttention(nn.Module):
    """Tiny self-attention block with spiking activation."""

    def __init__(self, dim: int, num_heads: int, snn_config: SNNConfig):
        super().__init__()
        self.attn = nn.MultiheadAttention(embed_dim=dim, num_heads=num_heads, batch_first=True)
        self.norm = nn.LayerNorm(dim)
        self.spike = SpikingActivation(
            threshold=snn_config.spike_threshold,
            surrogate_type=snn_config.surrogate_type
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        attn_out, _ = self.attn(x, x, x)
        x = self.norm(x + attn_out)
        return self.spike(x)


class SpikingTransformerBlock(nn.Module):
    """Transformer block with spiking activations.
    
    TODO: For larger teacher models (Llama-3.2-3B, Qwen-2.5-3B), consider:
    - Increasing dim to 256-512 for better capacity
    - Adding more sophisticated attention mechanisms (e.g., grouped query attention)
    - Using deeper networks (depth=4-8) with residual connections
    - Adding adaptive pooling to handle variable sequence lengths
    """
    
    def __init__(self, dim: int, num_heads: int, mlp_ratio: float, snn_config: SNNConfig):
        super().__init__()
        hidden = int(dim * mlp_ratio)
        self.attn = SpikingSelfAttention(dim, num_heads, snn_config)
        self.ff = nn.Sequential(
            nn.Linear(dim, hidden),
            nn.GELU(),
            SpikingActivation(
                threshold=snn_config.spike_threshold,
                surrogate_type=snn_config.surrogate_type
            ),
            nn.Linear(hidden, dim),
        )
        self.norm = nn.LayerNorm(dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.attn(x)
        x = self.norm(x + self.ff(x))
        return x


class SpikingStudentLM(nn.Module):
    """Minimal language model with spiking-friendly components.
    
    This is a demonstration architecture suitable for distilling from small teachers
    like tiny-gpt2. For production use with larger teachers (Llama-3.2-3B, Qwen-2.5-3B):
    
    TODO:
    - Scale up dim (e.g., 256-512) and depth (e.g., 4-8 layers)
    - Add position embeddings (learned or RoPE)
    - Implement more efficient attention mechanisms
    - Consider quantization-aware training for INT8 deployment
    - Add gradient checkpointing for memory efficiency during training
    """

    def __init__(
        self,
        vocab_size: int,
        dim: int = 128,
        depth: int = 2,
        num_heads: int = 4,
        snn_config: Optional[SNNConfig] = None
    ):
        super().__init__()
        self.snn_config = snn_config or SNNConfig()
        self.embed = nn.Embedding(vocab_size, dim)
        self.blocks = nn.ModuleList([
            SpikingTransformerBlock(dim, num_heads, mlp_ratio=2.0, snn_config=self.snn_config)
            for _ in range(depth)
        ])
        self.head = nn.Linear(dim, vocab_size)
        
        # Store architecture metadata
        self.architecture_version = "v1.0"
        self.dim = dim
        self.depth = depth
        self.num_heads = num_heads

    def forward(self, input_ids: torch.Tensor) -> torch.Tensor:
        x = self.embed(input_ids)
        for block in self.blocks:
            x = block(x)
        logits = self.head(x)
        return logits


# ------------------------ Training utilities ------------------------


def batch_iterable(data: Sequence[str], batch_size: int) -> Iterable[List[str]]:
    for i in range(0, len(data), batch_size):
        yield data[i : i + batch_size]


def tokenize_batch(prompts: Sequence[str], tokenizer, max_length: int, device: str):
    encoded = tokenizer(
        list(prompts),
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=max_length,
    )
    return {k: v.to(device) for k, v in encoded.items()}


def distillation_loss(student_logits: torch.Tensor, teacher_logits: torch.Tensor, temperature: float) -> torch.Tensor:
    # Align shapes: both [batch, seq, vocab]
    student_log_probs = F.log_softmax(student_logits / temperature, dim=-1)
    teacher_probs = F.softmax(teacher_logits / temperature, dim=-1)
    loss = F.kl_div(student_log_probs, teacher_probs, reduction="batchmean") * (temperature**2)
    return loss


def get_git_commit() -> Optional[str]:
    """Get current git commit hash if available."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def create_lr_scheduler(optimizer, config: TrainConfig):
    """Create learning rate scheduler based on config.
    
    Supports:
    - constant: No scheduling (default)
    - cosine: Cosine annealing with optional warmup
    - linear: Linear decay with optional warmup
    """
    if config.scheduler == "constant":
        return None
    
    if config.scheduler == "cosine":
        # Cosine annealing with warmup
        if config.warmup_steps > 0:
            def lr_lambda(step):
                if step < config.warmup_steps:
                    return step / config.warmup_steps
                progress = (step - config.warmup_steps) / (config.num_steps - config.warmup_steps)
                return 0.5 * (1 + math.cos(math.pi * progress))
        else:
            def lr_lambda(step):
                progress = step / config.num_steps
                return 0.5 * (1 + math.cos(math.pi * progress))
        return torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)
    
    elif config.scheduler == "linear":
        # Linear decay with warmup
        if config.warmup_steps > 0:
            def lr_lambda(step):
                if step < config.warmup_steps:
                    return step / config.warmup_steps
                return max(0.0, (config.num_steps - step) / (config.num_steps - config.warmup_steps))
        else:
            def lr_lambda(step):
                return max(0.0, (config.num_steps - step) / config.num_steps)
        return torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)
    
    else:
        raise ValueError(f"Unknown scheduler type: {config.scheduler}")


def export_student_to_onnx(artifact_dir: Path) -> None:
    """Export the trained student checkpoint to ONNX using the helper script."""

    export_script = Path(__file__).with_name("export_snn_to_onnx.py")
    model_path = artifact_dir / "student.pt"
    metadata_path = artifact_dir / "metadata.json"
    onnx_path = artifact_dir / "student.onnx"

    subprocess.run(
        [
            sys.executable,
            str(export_script),
            "--model-path",
            str(model_path),
            "--metadata-path",
            str(metadata_path),
            "--output-path",
            str(onnx_path),
        ],
        check=True,
    )


def train(config: TrainConfig):
    """Train a spiking student model via knowledge distillation.
    
    Args:
        config: Training configuration with hyperparameters
    """
    device = torch.device(config.device if torch.cuda.is_available() or "cuda" not in config.device else config.device)

    print(f"Loading teacher model: {config.teacher_model}")
    teacher_model, tokenizer = load_teacher_model(config.teacher_model, device)
    vocab_size = tokenizer.vocab_size

    print(f"Initializing student model with SNN config:")
    print(f"  - Timesteps: {config.snn_config.num_timesteps}")
    print(f"  - Surrogate: {config.snn_config.surrogate_type}")
    print(f"  - Threshold: {config.snn_config.spike_threshold}")
    
    student = SpikingStudentLM(vocab_size=vocab_size, snn_config=config.snn_config).to(device)
    student_param_count = sum(p.numel() for p in student.parameters())
    print(f"Student parameters: {student_param_count:,}")
    
    optimizer = torch.optim.AdamW(student.parameters(), lr=config.lr)
    scheduler = create_lr_scheduler(optimizer, config)
    if scheduler:
        print(f"Using {config.scheduler} LR scheduler with warmup_steps={config.warmup_steps}")

    prompts = load_prompts(config.dataset, config.dataset_path)
    if not prompts:
        raise ValueError("No prompts available for training")
    print(f"Loaded {len(prompts)} prompts from {config.dataset}")

    global_step = 0
    accum_steps = 0
    running_loss = 0.0

    student.train()
    for epoch in range(math.ceil(config.num_steps / max(1, len(prompts) // config.batch_size))):
        for batch_prompts in batch_iterable(prompts, config.batch_size):
            batch = tokenize_batch(batch_prompts, tokenizer, config.max_length, device)
            with torch.no_grad():
                teacher_out = teacher_model(**batch)
            teacher_logits = teacher_out.logits.detach()

            student_logits = student(batch["input_ids"])
            loss = distillation_loss(student_logits, teacher_logits, config.temperature)
            loss = loss / config.grad_accum_steps
            loss.backward()

            accum_steps += 1
            running_loss += loss.item()
            if accum_steps % config.grad_accum_steps == 0:
                optimizer.step()
                if scheduler:
                    scheduler.step()
                optimizer.zero_grad()
                global_step += 1

                if config.log_interval > 0 and global_step % config.log_interval == 0:
                    step_loss = running_loss * config.grad_accum_steps / accum_steps
                    current_lr = optimizer.param_groups[0]['lr']
                    print(f"Step {global_step}/{config.num_steps}: loss={step_loss:.4f}, lr={current_lr:.6f}")

                if global_step >= config.num_steps:
                    break

        if global_step >= config.num_steps:
            break

    avg_loss = running_loss / max(1, global_step)
    artifact_dir = Path(config.output_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    # Save model checkpoint
    torch.save(student.state_dict(), artifact_dir / "student.pt")
    
    # Create comprehensive metadata
    git_commit = get_git_commit() if config.track_git_commit else None
    metadata = {
        "model_type": student.__class__.__name__,
        "architecture_version": getattr(student, "architecture_version", "v1.0"),
        "vocab_size": vocab_size,
        "student_params": student_param_count,
        "architecture": {
            "dim": student.dim,
            "depth": student.depth,
            "num_heads": student.num_heads,
        },
        "snn_config": asdict(config.snn_config),
        "training_config": {
            "num_steps": config.num_steps,
            "batch_size": config.batch_size,
            "grad_accum_steps": config.grad_accum_steps,
            "teacher_model": config.teacher_model,
            "lr": config.lr,
            "scheduler": config.scheduler,
            "warmup_steps": config.warmup_steps,
            "temperature": config.temperature,
            "dataset": config.dataset,
            "max_length": config.max_length,
        },
        "config": asdict(config),
        "training_results": {
            "steps": global_step,
            "avg_loss": avg_loss,
        },
        "metadata": {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "git_commit": git_commit,
        }
    }
    (artifact_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
    
    if config.export_onnx:
        print("Exporting ONNX artifact...")
        export_student_to_onnx(artifact_dir)

    print(f"\nTraining complete!")
    print(f"  Steps: {global_step}")
    print(f"  Avg loss: {avg_loss:.4f}")
    print(f"  Student params: {student_param_count:,}")
    print(f"  Artifacts: {artifact_dir}")
    if git_commit:
        print(f"  Git commit: {git_commit[:8]}")


# ------------------------ Entry point ------------------------


def parse_args() -> TrainConfig:
    """Parse command-line arguments for SNN student training.
    
    Returns:
        TrainConfig with all hyperparameters and settings
    """
    parser = argparse.ArgumentParser(
        description="Train a spiking student model via knowledge distillation from a teacher LM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Demo training with tiny teacher (Colab-friendly)
  %(prog)s --teacher-model sshleifer/tiny-gpt2 --dataset synthetic --num-steps 50

  # Production training with Llama-3.2-3B teacher
  %(prog)s --teacher-model meta-llama/Llama-3.2-3B --dataset wikitext-2 \\
    --num-steps 10000 --batch-size 4 --grad-accum-steps 8 --max-length 512 \\
    --lr 3e-4 --scheduler cosine --warmup-steps 500 \\
    --snn-timesteps 8 --snn-surrogate fast_sigmoid --snn-threshold 0.5

  # Training with Qwen-2.5-3B teacher
  %(prog)s --teacher-model Qwen/Qwen2.5-3B --dataset wikitext-2 \\
    --num-steps 10000 --batch-size 2 --grad-accum-steps 16 \\
    --max-length 1024 --scheduler linear --warmup-steps 1000
        """
    )
    
    # Required arguments
    parser.add_argument(
        "--teacher-model",
        type=str,
        required=True,
        help="Hugging Face model id or local path for the teacher (e.g., sshleifer/tiny-gpt2, "
             "meta-llama/Llama-3.2-3B, Qwen/Qwen2.5-3B)",
    )
    
    # Dataset arguments
    parser.add_argument(
        "--dataset",
        type=str,
        default="wikitext-2",
        help="Dataset name for prompts (e.g., wikitext-2, synthetic, or any `datasets`-compatible id)",
    )
    parser.add_argument(
        "--dataset-path",
        type=str,
        default=None,
        help="Optional path to a prompts text file (one prompt per line)"
    )
    
    # Output arguments
    parser.add_argument(
        "--output-dir",
        type=str,
        default="artifacts/snn_student",
        help="Directory for artifacts (default: artifacts/snn_student)",
    )
    parser.add_argument(
        "--export-onnx",
        action="store_true",
        help="Export the trained student to ONNX using export_snn_to_onnx.py",
    )
    
    # Training hyperparameters
    parser.add_argument(
        "--lr",
        type=float,
        default=1e-4,
        help="Student learning rate for AdamW optimizer (default: 1e-4)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=2,
        help="Batch size per optimization step (default: 2, Colab-friendly)",
    )
    parser.add_argument(
        "--grad-accum-steps",
        type=int,
        default=4,
        help="Gradient accumulation steps (effective batch = batch-size * grad-accum-steps)",
    )
    parser.add_argument(
        "--num-steps",
        type=int,
        default=20,
        help="Number of optimization steps (default: 20 for demo, use 10000+ for production)",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=64,
        help="Maximum tokenized length for prompts (default: 64, use 512-1024 for larger teachers)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=1.0,
        help="Distillation temperature for soft targets (default: 1.0)",
    )
    
    # Learning rate schedule
    parser.add_argument(
        "--scheduler",
        type=str,
        default="constant",
        choices=["constant", "cosine", "linear"],
        help="Learning rate schedule type (default: constant)",
    )
    parser.add_argument(
        "--warmup-steps",
        type=int,
        default=0,
        help="Number of warmup steps for LR scheduler (default: 0)",
    )
    
    # SNN-specific hyperparameters
    parser.add_argument(
        "--snn-timesteps",
        type=int,
        default=4,
        help="Number of simulation timesteps for spiking neurons (default: 4)",
    )
    parser.add_argument(
        "--snn-surrogate",
        type=str,
        default="sigmoid",
        choices=["sigmoid", "fast_sigmoid", "triangular", "arctan"],
        help="Surrogate gradient function for SNN training (default: sigmoid)",
    )
    parser.add_argument(
        "--snn-threshold",
        type=float,
        default=1.0,
        help="Spike threshold for spiking neurons (default: 1.0)",
    )
    
    # Logging and device
    parser.add_argument(
        "--log-interval",
        type=int,
        default=5,
        help="Steps between loss logs, 0 to disable (default: 5)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda" if torch.cuda.is_available() else "cpu",
        help="Training device (default: auto-detect cuda/cpu)",
    )
    
    # Metadata tracking
    parser.add_argument(
        "--no-git-tracking",
        action="store_true",
        help="Disable git commit tracking in metadata",
    )
    
    args = parser.parse_args()
    
    # Build SNN config
    snn_config = SNNConfig(
        num_timesteps=args.snn_timesteps,
        surrogate_type=args.snn_surrogate,
        spike_threshold=args.snn_threshold,
    )
    
    return TrainConfig(
        teacher_model=args.teacher_model,
        dataset=args.dataset,
        dataset_path=args.dataset_path,
        output_dir=args.output_dir,
        lr=args.lr,
        batch_size=args.batch_size,
        grad_accum_steps=args.grad_accum_steps,
        num_steps=args.num_steps,
        log_interval=args.log_interval,
        device=args.device,
        max_length=args.max_length,
        temperature=args.temperature,
        export_onnx=args.export_onnx,
        scheduler=args.scheduler,
        warmup_steps=args.warmup_steps,
        snn_config=snn_config,
        track_git_commit=not args.no_git_tracking,
    )


def main():
    """Main entry point for SNN student training."""
    config = parse_args()
    train(config)


if __name__ == "__main__":
    main()
