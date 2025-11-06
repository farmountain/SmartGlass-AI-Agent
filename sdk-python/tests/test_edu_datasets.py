"""Smoke tests for education-focused synthetic datasets."""

from __future__ import annotations

import json

import onnxruntime as ort
import pytest
import torch

from sdk_python.skill_template import export_onnx, trainer
from sdk_python.skills_impl import load_y_form_parser


@pytest.mark.parametrize(
    "dataset",
    ["edu_linear_eq", "edu_ratio_percent", "edu_geo_basic"],
)
def test_edu_dataset_training_pipeline(tmp_path, dataset):
    config = trainer.SkillTrainerConfig(
        dataset=dataset,
        epochs=5,
        learning_rate=0.05,
        hidden_dim=8,
        train_samples=100,
        eval_samples=32,
        seed=7,
        weight_decay=0.0,
        noise_floor=1e-3,
    )
    skill_trainer = trainer.SkillTrainer(config)
    fit_result = skill_trainer.fit()
    assert fit_result.final_loss >= 0.0

    calibration = trainer.load_dataset(
        dataset,
        "validation",
        samples=config.eval_samples,
        seed=config.seed + 1,
    )
    train_dataset = trainer.load_dataset(
        dataset,
        "train",
        samples=config.train_samples,
        seed=config.seed,
    )

    parser = load_y_form_parser(dataset)
    examples = parser(train_dataset.features[:5])
    assert len(examples) == 5
    assert all(isinstance(example, str) and example for example in examples)

    export_dir = tmp_path / dataset
    export_config = export_onnx.ExportConfig(
        skill_id=f"{dataset}_smoke",
        model=skill_trainer.get_model(),
        sample_input=calibration.features,
        targets=train_dataset.targets,
        output_dir=export_dir,
    )
    export_result = export_onnx.export_int8(export_config)

    assert export_result.model_path.exists()
    assert export_result.stats_path.exists()

    session = ort.InferenceSession(str(export_result.model_path))
    outputs = session.run(
        None,
        {"input": calibration.features.detach().cpu().numpy()},
    )
    assert outputs and len(outputs[0]) == calibration.features.shape[0]

    stats_payload = json.loads(export_result.stats_path.read_text())
    assert stats_payload["num_targets"] == config.train_samples

    with torch.no_grad():
        predictions, _ = skill_trainer.predict(calibration.features)
    assert predictions.shape[0] == calibration.features.shape[0]
