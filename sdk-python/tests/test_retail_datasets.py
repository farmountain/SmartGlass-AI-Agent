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
        ("rt_wtp_radar", 5, "WTP Radar input"),
        ("rt_capsule_gaps", 5, "Capsule Gaps input"),
        ("rt_minute_meal", 5, "Minute Meal input"),
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


class TestWTPBoundaryBehavior:
    """Test willingness-to-pay edge cases and boundary scenarios."""

    def test_min_wtp_scenario(self):
        """Test minimum WTP: low brand, low income, low uniqueness, low competitor ratio."""
        dataset_name = "rt_wtp_radar"
        dataset = load_synthesized_dataset(dataset_name, "test", num_samples=100, seed=42)
        
        # Check that WTP values are positive (customers still willing to pay something)
        assert torch.all(dataset.targets > 0), "WTP should always be positive"
        
        # Find scenarios with low brand/income/uniqueness and LOW competitor ratio
        # (low competitor ratio = competitors are cheaper, unfavorable for us)
        features = dataset.features
        low_brand_mask = features[:, 1] < 0.3
        low_income_mask = features[:, 2] < 0.3
        low_competitor_mask = features[:, 4] < 0.9  # Competitors are cheaper
        
        min_scenario_mask = low_brand_mask & low_income_mask & low_competitor_mask
        if torch.any(min_scenario_mask):
            min_wtps = dataset.targets[min_scenario_mask]
            # These should be lower than average
            avg_wtp = dataset.targets.mean()
            assert min_wtps.mean() < avg_wtp

    def test_max_wtp_scenario(self):
        """Test maximum WTP: high brand, high income, high uniqueness, high competitor ratio."""
        dataset_name = "rt_wtp_radar"
        dataset = load_synthesized_dataset(dataset_name, "test", num_samples=200, seed=42)
        
        features = dataset.features
        high_brand_mask = features[:, 1] > 0.65
        high_income_mask = features[:, 2] > 0.65
        high_competitor_mask = features[:, 4] > 1.15  # Competitors are more expensive
        
        max_scenario_mask = high_brand_mask & high_income_mask & high_competitor_mask
        if torch.any(max_scenario_mask):
            max_wtps = dataset.targets[max_scenario_mask]
            # These should be higher than average
            avg_wtp = dataset.targets.mean()
            # With enough samples matching criteria, this should hold
            if len(max_wtps) >= 5:
                assert max_wtps.mean() > avg_wtp

    def test_wtp_increases_with_brand_score(self):
        """Test that WTP generally increases with brand reputation."""
        dataset_name = "rt_wtp_radar"
        dataset = load_synthesized_dataset(dataset_name, "test", num_samples=200, seed=999)
        
        features = dataset.features
        brand_scores = features[:, 1]
        
        # Split into low and high brand score groups
        low_brand = dataset.targets[brand_scores < 0.4]
        high_brand = dataset.targets[brand_scores > 0.6]
        
        if len(low_brand) > 0 and len(high_brand) > 0:
            # On average, high brand should yield higher WTP
            assert high_brand.mean() > low_brand.mean()

    def test_wtp_sensitivity_to_competitor_pricing(self):
        """Test that WTP increases when competitor ratio is higher (competitors more expensive)."""
        dataset_name = "rt_wtp_radar"
        dataset = load_synthesized_dataset(dataset_name, "test", num_samples=200, seed=777)
        
        features = dataset.features
        competitor_ratios = features[:, 4]
        
        # Low competitor ratio means competitors are cheaper (unfavorable for us)
        # High competitor ratio means competitors are more expensive (favorable for us)
        unfavorable = dataset.targets[competitor_ratios < 0.9]
        favorable = dataset.targets[competitor_ratios > 1.2]
        
        if len(favorable) > 0 and len(unfavorable) > 0:
            # Favorable scenarios should yield higher WTP
            assert favorable.mean() > unfavorable.mean()
