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
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

import torch
from torch import nn
from torch.nn import functional as F


@dataclass
class TrainConfig:
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
    device = torch.device(config.device if torch.cuda.is_available() or "cuda" not in config.device else config.device)

    teacher_model, tokenizer = load_teacher_model(config.teacher_model, device)
    vocab_size = tokenizer.vocab_size

    student = SpikingStudentLM(vocab_size=vocab_size).to(device)
    student_param_count = sum(p.numel() for p in student.parameters())
    optimizer = torch.optim.AdamW(student.parameters(), lr=config.lr)

    prompts = load_prompts(config.dataset, config.dataset_path)
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

                if config.log_interval > 0 and global_step % config.log_interval == 0:
                    step_loss = running_loss * config.grad_accum_steps / accum_steps
                    print(f"Step {global_step}/{config.num_steps}: loss={step_loss:.4f}")

                if global_step >= config.num_steps:
                    break

        if global_step >= config.num_steps:
            break

    avg_loss = running_loss / max(1, global_step)
    artifact_dir = Path(config.output_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    torch.save(student.state_dict(), artifact_dir / "student.pt")
    metadata = {
        "model_type": student.__class__.__name__,
        "vocab_size": vocab_size,
        "student_params": student_param_count,
        "training_config": {
            "num_steps": config.num_steps,
            "batch_size": config.batch_size,
            "teacher_model": config.teacher_model,
            "lr": config.lr,
            "temperature": config.temperature,
            "dataset": config.dataset,
        },
        "config": asdict(config),
        "steps": global_step,
        "avg_loss": avg_loss,
    }
    (artifact_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
    if config.export_onnx:
        print("Exporting ONNX artifact...")
        export_student_to_onnx(artifact_dir)

    print(f"Training complete. Steps: {global_step}, avg_loss: {avg_loss:.4f}")
    print(f"Student params: {student_param_count}")
    print(f"Artifacts: {artifact_dir}")


# ------------------------ Entry point ------------------------


def parse_args() -> TrainConfig:
    parser = argparse.ArgumentParser(description="Train a spiking student via KD")
    parser.add_argument(
        "--teacher-model",
        type=str,
        required=True,
        help="Required Hugging Face model id or local path for the teacher (e.g., sshleifer/tiny-gpt2)",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="wikitext-2",
        help="Dataset name for prompts (e.g., wikitext-2, synthetic, or any `datasets`-compatible id)",
    )
    parser.add_argument("--dataset-path", type=str, default=None, help="Optional path to a prompts text file")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="artifacts/snn_student",
        help="Directory for artifacts (default: artifacts/snn_student)",
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=1e-4,
        help="Student learning rate (AdamW)",
    )
    parser.add_argument("--batch-size", type=int, default=2, help="Batch size (Colab-friendly)")
    parser.add_argument("--grad-accum-steps", type=int, default=4, help="Gradient accumulation steps")
    parser.add_argument("--num-steps", type=int, default=20, help="Number of optimization steps")
    parser.add_argument("--log-interval", type=int, default=5, help="Steps between loss logs (0 to disable)")
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu", help="Training device")
    parser.add_argument(
        "--max-length",
        type=int,
        default=64,
        help="Maximum tokenized length for prompts",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=1.0,
        help="Distillation temperature for soft targets",
    )
    parser.add_argument(
        "--export-onnx",
        action="store_true",
        help="Export the trained student to ONNX using export_snn_to_onnx.py",
    )
    args = parser.parse_args()
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
    )


def main():
    config = parse_args()
    train(config)


if __name__ == "__main__":
    main()
