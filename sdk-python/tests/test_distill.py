"""End-to-end tests covering the offline distillation loop."""

import torch

from sdk_python.distill import distill
from sdk_python.skill_template.trainer import SkillTrainer, SkillTrainerConfig


def _closed_form_teacher(features: torch.Tensor) -> torch.Tensor:
    """Return noise-free y-values for ``edu_linear_eq`` features."""

    slope = features[:, 0:1]
    intercept = features[:, 1:2]
    x_value = features[:, 2:3]
    return slope * x_value + intercept


def test_run_once_reduces_loss_and_logs_supervision(monkeypatch):
    # Patch the teacher lookups so the student always receives perfect targets.
    monkeypatch.setattr(distill, "get_teacher_outputs", lambda skill, feats: _closed_form_teacher(feats))
    from sdk_python.distill import teachers

    monkeypatch.setattr(
        teachers,
        "get_teacher_outputs",
        lambda skill, feats: _closed_form_teacher(feats),
    )

    config = SkillTrainerConfig(
        dataset="edu_linear_eq",
        epochs=12,
        learning_rate=0.05,
        hidden_dim=8,
        train_samples=32,
        lam_align=1.0,
        seed=7,
    )
    student = SkillTrainer(config)

    step = distill.run_once(
        student=student,
        skill="edu_linear_eq",
        step=1,
        preview_samples=6,
    )

    history = step.fit_result.loss_history
    assert len(history) >= 2
    assert history[0] > history[-1], "Training loss should decrease over the run."

    expected_targets = _closed_form_teacher(step.preview_dataset.features)
    torch.testing.assert_close(step.supervision_targets, expected_targets)

    features, targets = step.supervision_pair()
    torch.testing.assert_close(features, step.preview_dataset.features)
    torch.testing.assert_close(targets, expected_targets)
