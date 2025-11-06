"""Smoke tests for the SDK Python skill template."""

import argparse
import json
from argparse import Namespace

import pytest

from sdk_python import raycli
from sdk_python.edu import load_configs
from sdk_python.skill_template import export_onnx, eval as eval_module, trainer


@pytest.mark.parametrize(
    "module",
    [trainer, export_onnx, eval_module],
)
def test_modules_importable(module):
    """Ensure each template module can be imported without side effects."""
    assert module is not None


def test_workflows_execute(tmp_path):
    args = Namespace(
        dataset="math_reasoning_v1",
        epochs=5,
        learning_rate=0.05,
        hidden_dim=8,
        train_samples=64,
        eval_samples=8,
        seed=0,
        weight_decay=0.0,
        noise_floor=1e-3,
    )
    trainer.run(args)

    export_path = tmp_path / "model.onnx"
    args = Namespace(output=str(export_path), validation_seconds=0.0)
    export_onnx.run(args)
    assert export_path.exists()

    eval_args = Namespace(samples=1, sleep=0.0)
    eval_module.run(eval_args)


def test_cli_parser_exposes_commands():
    parser = raycli.build_parser()
    subparsers_action = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )
    expected = {"train", "export", "eval", "train_pack"}
    assert expected.issubset(set(subparsers_action.choices.keys()))


def test_train_pack_command_generates_artifacts(tmp_path):
    output_root = tmp_path / "skills"
    args = [
        "train_pack",
        "--output-root",
        str(output_root),
        "--epochs",
        "1",
        "--learning-rate",
        "0.01",
        "--validation-seconds",
        "0.0",
    ]

    exit_code = raycli.main(args)
    assert exit_code == 0

    configs = load_configs()
    models_dir = output_root / "models"
    stats_dir = output_root / "stats"

    assert models_dir.is_dir()
    assert stats_dir.is_dir()

    expected_model_files = {config.model_basename for config in configs}
    expected_stats_files = {config.stats_basename for config in configs}

    actual_model_files = {path.name for path in models_dir.iterdir()}
    actual_stat_files = {path.name for path in stats_dir.iterdir()}

    assert actual_model_files == expected_model_files
    assert actual_stat_files == expected_stats_files

    sample = configs[0]
    model_path = models_dir / sample.model_basename
    stats_path = stats_dir / sample.stats_basename

    assert model_path.read_text().strip() == "mock onnx data"

    stats_payload = json.loads(stats_path.read_text())
    assert stats_payload["skill_id"] == sample.skill_id
    assert stats_payload["training"]["epochs"] == 1
