"""Smoke tests for the SDK Python skill template."""

import argparse
import json
from argparse import Namespace

import onnxruntime as ort
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

    export_args = Namespace(
        skill_id="demo_skill",
        output_dir=tmp_path,
        opset_version=17,
        dataset=args.dataset,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        hidden_dim=args.hidden_dim,
        train_samples=args.train_samples,
        eval_samples=args.eval_samples,
        seed=args.seed,
        weight_decay=args.weight_decay,
        noise_floor=args.noise_floor,
    )
    export_onnx.run(export_args)

    model_path = tmp_path / "demo_skill_int8.onnx"
    stats_path = tmp_path / "demo_skill_stats.json"

    assert model_path.exists()
    assert stats_path.exists()

    session = ort.InferenceSession(str(model_path))
    assert session is not None

    stats_payload = json.loads(stats_path.read_text())
    assert stats_payload["skill_id"] == "demo_skill"
    assert "y_mean" in stats_payload
    assert "y_std" in stats_payload


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

    assert model_path.exists()
    session = ort.InferenceSession(str(model_path))
    assert session is not None

    stats_payload = json.loads(stats_path.read_text())
    assert stats_payload["skill_id"] == sample.skill_id
    assert "y_mean" in stats_payload
    assert "y_std" in stats_payload
