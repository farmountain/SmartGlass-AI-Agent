"""Training script for a lightweight spiking student model with KD.

This script provides a minimal pipeline for distilling a teacher language
model into a small spiking-friendly student. It is designed to be easy to run
in constrained environments (e.g., Google Colab) with configurable batch sizes
and gradient accumulation.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

import torch
from torch import nn
from torch.nn import functional as F


@dataclass
class TrainConfig:
    teacher_model: str
    dataset_path: Optional[str]
    output_dir: str
    lr: float
    batch_size: int
    grad_accum_steps: int
    num_steps: int
    device: str
    max_length: int
    temperature: float


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


def load_prompts(dataset_path: Optional[str]) -> List[str]:
    """Load prompts from a text file or fall back to synthetic samples."""

    if dataset_path:
        path = Path(dataset_path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset path {dataset_path} does not exist")
        return [line.strip() for line in path.read_text().splitlines() if line.strip()]

    # Lightweight synthetic prompts to avoid external dependencies.
    return [
        "Describe a sunrise over the mountains.",
        "List three safety tips for biking in the city.",
        "Write a short haiku about technology.",
        "Explain knowledge distillation in simple terms.",
        "Suggest a healthy lunch recipe with avocado.",
    ]


# ------------------------ Student model ------------------------


class SpikingActivation(nn.Module):
    """Approximate spiking activation with surrogate gradient."""

    def __init__(self, threshold: float = 1.0):
        super().__init__()
        self.threshold = threshold

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Straight-through estimator for spike generation.
        out = (x > self.threshold).float()
        # Surrogate gradient: derivative of sigmoid for smooth backprop.
        return out + torch.sigmoid(x - self.threshold) - torch.sigmoid(x - self.threshold).detach()


class SpikingSelfAttention(nn.Module):
    """Tiny self-attention block with spiking activation."""

    def __init__(self, dim: int, num_heads: int):
        super().__init__()
        self.attn = nn.MultiheadAttention(embed_dim=dim, num_heads=num_heads, batch_first=True)
        self.norm = nn.LayerNorm(dim)
        self.spike = SpikingActivation()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        attn_out, _ = self.attn(x, x, x)
        x = self.norm(x + attn_out)
        return self.spike(x)


class SpikingTransformerBlock(nn.Module):
    def __init__(self, dim: int, num_heads: int, mlp_ratio: float = 2.0):
        super().__init__()
        hidden = int(dim * mlp_ratio)
        self.attn = SpikingSelfAttention(dim, num_heads)
        self.ff = nn.Sequential(
            nn.Linear(dim, hidden),
            nn.GELU(),
            SpikingActivation(),
            nn.Linear(hidden, dim),
        )
        self.norm = nn.LayerNorm(dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.attn(x)
        x = self.norm(x + self.ff(x))
        return x


class SpikingStudentLM(nn.Module):
    """Minimal language model with spiking-friendly components."""

    def __init__(self, vocab_size: int, dim: int = 128, depth: int = 2, num_heads: int = 4):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, dim)
        self.blocks = nn.ModuleList([SpikingTransformerBlock(dim, num_heads) for _ in range(depth)])
        self.head = nn.Linear(dim, vocab_size)

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


def train(config: TrainConfig):
    device = torch.device(config.device if torch.cuda.is_available() or "cuda" not in config.device else config.device)

    teacher_model, tokenizer = load_teacher_model(config.teacher_model, device)
    vocab_size = tokenizer.vocab_size

    student = SpikingStudentLM(vocab_size=vocab_size).to(device)
    optimizer = torch.optim.AdamW(student.parameters(), lr=config.lr)

    prompts = load_prompts(config.dataset_path)
    if not prompts:
        raise ValueError("No prompts available for training")

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
                optimizer.zero_grad()
                global_step += 1

                if global_step >= config.num_steps:
                    break

        if global_step >= config.num_steps:
            break

    avg_loss = running_loss / max(1, global_step)
    artifact_dir = Path(config.output_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    torch.save(student.state_dict(), artifact_dir / "student.pt")
    metadata = {
        "config": asdict(config),
        "steps": global_step,
        "avg_loss": avg_loss,
    }
    (artifact_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
    print(f"Training complete. Steps: {global_step}, avg_loss: {avg_loss:.4f}")
    print(f"Artifacts saved to: {artifact_dir}")


# ------------------------ Entry point ------------------------


def parse_args() -> TrainConfig:
    parser = argparse.ArgumentParser(description="Train a spiking student via KD")
    parser.add_argument("--teacher-model", type=str, default="sshleifer/tiny-gpt2", help="Hugging Face model id or local path")
    parser.add_argument("--dataset-path", type=str, default=None, help="Optional path to prompts text file")
    parser.add_argument("--output-dir", type=str, default="artifacts/snn_student", help="Directory for artifacts")
    parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate")
    parser.add_argument("--batch-size", type=int, default=2, help="Batch size (Colab-friendly)")
    parser.add_argument("--grad-accum-steps", type=int, default=4, help="Gradient accumulation steps")
    parser.add_argument("--num-steps", type=int, default=20, help="Number of optimization steps")
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu", help="Training device")
    parser.add_argument("--max-length", type=int, default=64, help="Maximum tokenized length")
    parser.add_argument("--temperature", type=float, default=1.0, help="Distillation temperature")
    args = parser.parse_args()
    return TrainConfig(
        teacher_model=args.teacher_model,
        dataset_path=args.dataset_path,
        output_dir=args.output_dir,
        lr=args.lr,
        batch_size=args.batch_size,
        grad_accum_steps=args.grad_accum_steps,
        num_steps=args.num_steps,
        device=args.device,
        max_length=args.max_length,
        temperature=args.temperature,
    )


def main():
    config = parse_args()
    train(config)


if __name__ == "__main__":
    main()
