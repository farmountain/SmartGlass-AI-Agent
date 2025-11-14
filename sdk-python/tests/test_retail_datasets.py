"""Unit tests for retail-oriented synthetic datasets."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import torch

_SKILLS_IMPL_DIR = Path(__file__).resolve().parents[1] / "sdk_python" / "skills_impl"
_SKILLS_IMPL_INIT = _SKILLS_IMPL_DIR / "__init__.py"
_spec = importlib.util.spec_from_file_location(
    "retail_skills_impl",
    _SKILLS_IMPL_INIT,
    submodule_search_locations=[str(_SKILLS_IMPL_DIR)],
)
assert _spec and _spec.loader  # sanity check for test runtime
_skills_impl = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _skills_impl
_spec.loader.exec_module(_skills_impl)

load_synthesized_dataset = _skills_impl.load_synthesized_dataset
load_y_form_parser = _skills_impl.load_y_form_parser


@pytest.mark.parametrize(
    ("dataset_name", "feature_dim", "expected_phrase"),
    [
        ("rt_wtp_radar", 6, "WTP radar input"),
        ("rt_capsule_gaps", 5, "Capsule gap input"),
        ("rt_minute_meal", 5, "Minute meal input"),
    ],
)
class TestRetailDatasets:
    def test_shapes_and_types(self, dataset_name: str, feature_dim: int, expected_phrase: str):
        dataset = load_synthesized_dataset(
            dataset_name, "train", num_samples=24, seed=101
        )
        assert dataset.features.shape == (24, feature_dim)
        assert dataset.targets.shape == (24, 1)
        assert dataset.features.dtype == torch.float32
        assert dataset.targets.dtype == torch.float32
        assert dataset.noise_std > 0.0

    def test_reproducibility(self, dataset_name: str, feature_dim: int, expected_phrase: str):
        kwargs = dict(split="validation", num_samples=12, seed=7)
        first = load_synthesized_dataset(dataset_name, **kwargs)
        second = load_synthesized_dataset(dataset_name, **kwargs)
        assert torch.equal(first.features, second.features)
        assert torch.equal(first.targets, second.targets)

    def test_features_to_y_form(self, dataset_name: str, feature_dim: int, expected_phrase: str):
        dataset = load_synthesized_dataset(
            dataset_name, "test", num_samples=5, seed=17
        )
        parser = load_y_form_parser(dataset_name)
        sentences = parser(dataset.features)
        assert len(sentences) == dataset.features.shape[0]
        assert all(isinstance(sentence, str) for sentence in sentences)
        assert all(sentence for sentence in sentences)
        assert any(expected_phrase in sentence for sentence in sentences)


def test_wtp_radar_boundaries() -> None:
    from sdk_python.skills_impl import rt_wtp_radar

    min_features = torch.tensor(
        [[20.0, 0.0, 0.0, 1.0, 0.0, 1.0]], dtype=torch.float32
    )
    max_features = torch.tensor(
        [[240.0, 1.0, 1.0, 0.0, 1.0, 0.0]], dtype=torch.float32
    )

    min_wtp = rt_wtp_radar.estimate_wtp(min_features)
    max_wtp = rt_wtp_radar.estimate_wtp(max_features)

    assert pytest.approx(rt_wtp_radar.MIN_WTP) == min_wtp.item()
    assert pytest.approx(rt_wtp_radar.MAX_WTP) == max_wtp.item()

    dataset = load_synthesized_dataset("rt_wtp_radar", "train", num_samples=128, seed=5)
    assert torch.all(dataset.targets >= rt_wtp_radar.MIN_WTP - 1e-6)
    assert torch.all(dataset.targets <= rt_wtp_radar.MAX_WTP + 1e-6)

