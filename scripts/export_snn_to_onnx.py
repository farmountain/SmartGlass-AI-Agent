import argparse
import json
from pathlib import Path

import torch

from scripts.train_snn_student import SpikingStudentLM


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export SpikingStudentLM to ONNX")
    parser.add_argument(
        "--model-path",
        type=str,
        required=True,
        help="Path to the trained student PyTorch checkpoint (student.pt)",
    )
    parser.add_argument(
        "--metadata-path",
        type=str,
        required=True,
        help="Path to metadata.json generated during training",
    )
    parser.add_argument(
        "--output-path",
        type=str,
        required=True,
        help="Destination for the exported ONNX model",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    metadata = json.loads(Path(args.metadata_path).read_text())
    vocab_size = metadata["vocab_size"]

    model = SpikingStudentLM(vocab_size=vocab_size)
    state_dict = torch.load(args.model_path, map_location="cpu")
    model.load_state_dict(state_dict)
    model.eval()

    dummy_input = torch.zeros((1, 4), dtype=torch.long)

    dynamic_axes = {
        "input_ids": {1: "seq_len"},
        "logits": {1: "seq_len"},
    }

    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    torch.onnx.export(
        model,
        dummy_input,
        output_path,
        input_names=["input_ids"],
        output_names=["logits"],
        dynamic_axes=dynamic_axes,
        opset_version=17,
    )

    print(f"Exported ONNX model to {output_path}")


if __name__ == "__main__":
    main()
