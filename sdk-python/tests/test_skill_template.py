"""Smoke tests for the SDK Python skill template."""

import argparse
from argparse import Namespace

import pytest

from sdk_python import raycli
from sdk_python.skill_template import export_onnx, eval as eval_module, trainer


@pytest.mark.parametrize(
    "module",
    [trainer, export_onnx, eval_module],
)
def test_modules_importable(module):
    """Ensure each template module can be imported without side effects."""
    assert module is not None


def test_mock_workflows_execute(tmp_path):
    config = trainer.TrainingConfig(epochs=2, sleep_seconds=0.01)
    mock_trainer = trainer.MockTrainer(config)
    mock_trainer.train()

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
    expected = {"train", "export", "eval"}
    assert expected.issubset(set(subparsers_action.choices.keys()))
