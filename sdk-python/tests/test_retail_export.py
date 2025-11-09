"""Unit tests for retail dataset export functionality."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import torch

from sdk_python.skill_template import trainer, export_onnx


@pytest.mark.parametrize(
    "dataset_name",
    ["rt_wtp_radar", "rt_capsule_gaps", "rt_minute_meal"],
)
class TestRetailDatasetExport:
    """Test that retail datasets can be trained and exported to ONNX."""

    def test_dataset_can_be_trained(self, dataset_name: str):
        """Test that the trainer can fit on the retail dataset."""
        config = trainer.SkillTrainerConfig(
            dataset=dataset_name,
            epochs=10,
            train_samples=64,
            eval_samples=16,
            seed=42,
        )
        skill_trainer = trainer.SkillTrainer(config)
        result = skill_trainer.fit()
        
        assert result.final_loss >= 0
        assert result.residual_std >= config.noise_floor
        
        # Verify predictions work
        validation = trainer.load_dataset(
            dataset_name, "validation", config.eval_samples, config.seed + 1
        )
        preds, sigma = skill_trainer.predict(validation.features)
        
        assert preds.shape == (config.eval_samples, 1)
        assert sigma.shape == (config.eval_samples, 1)
        assert torch.all(sigma > 0)

    def test_dataset_can_be_exported_to_onnx(self, dataset_name: str):
        """Test that the trained model can be exported to ONNX."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            skill_id = f"retail_{dataset_name}"
            
            # Train a small model
            config = trainer.SkillTrainerConfig(
                dataset=dataset_name,
                epochs=5,
                train_samples=32,
                eval_samples=8,
                seed=42,
            )
            skill_trainer = trainer.SkillTrainer(config)
            skill_trainer.fit()
            
            # Export to ONNX
            calibration = trainer.load_dataset(
                dataset_name, "validation", config.eval_samples, config.seed + 1
            )
            train_dataset = trainer.load_dataset(
                dataset_name, "train", config.train_samples, config.seed
            )
            
            export_config = export_onnx.ExportConfig(
                skill_id=skill_id,
                model=skill_trainer.get_model(),
                sample_input=calibration.features,
                targets=train_dataset.targets,
                output_dir=output_dir,
            )
            result = export_onnx.export_int8(export_config)
            
            # Verify artifacts were created
            assert result.model_path.exists()
            assert result.stats_path.exists()
            assert result.model_path.suffix == ".onnx"
            assert result.stats_path.suffix == ".json"
            
            # Verify stats content
            stats = result.stats
            assert stats["skill_id"] == skill_id
            assert "y_mean" in stats
            assert "y_std" in stats
            assert "num_targets" in stats
            assert stats["num_targets"] == config.train_samples
