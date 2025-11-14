"""
Unit tests for sigma threshold gating in health skills.

Tests verify that the sigma_gate_decide functions correctly enforce
confidence thresholds for health-related skills.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from skills import hc_gait_guard, hc_med_sentinel, hc_sun_hydro


class TestGaitGuardSigmaGate:
    """Test sigma gating for hc_gait_guard skill."""

    def test_sigma_gate_threshold(self):
        """Verify SIGMA_GATE constant is set correctly."""
        assert hc_gait_guard.SIGMA_GATE == 0.82

    def test_confidence_above_threshold_proceeds(self):
        """Confidence above sigma gate should return proceed."""
        decision = hc_gait_guard.sigma_gate_decide(0.85)
        assert decision == "proceed"

    def test_confidence_at_threshold_proceeds(self):
        """Confidence equal to sigma gate should return proceed."""
        decision = hc_gait_guard.sigma_gate_decide(0.82)
        assert decision == "proceed"

    def test_confidence_below_threshold_asks(self):
        """Confidence below sigma gate should return ask."""
        decision = hc_gait_guard.sigma_gate_decide(0.75)
        assert decision == "ask"

    def test_very_low_confidence_asks(self):
        """Very low confidence should return ask."""
        decision = hc_gait_guard.sigma_gate_decide(0.20)
        assert decision == "ask"

    def test_custom_threshold(self):
        """Custom threshold should override default."""
        decision = hc_gait_guard.sigma_gate_decide(0.75, threshold=0.70)
        assert decision == "proceed"

        decision = hc_gait_guard.sigma_gate_decide(0.75, threshold=0.80)
        assert decision == "ask"


class TestMedSentinelSigmaGate:
    """Test sigma gating for hc_med_sentinel skill."""

    def test_sigma_gate_threshold(self):
        """Verify SIGMA_GATE constant is set correctly."""
        assert hc_med_sentinel.SIGMA_GATE == 0.88

    def test_confidence_above_threshold_proceeds(self):
        """Confidence above sigma gate should return proceed."""
        decision = hc_med_sentinel.sigma_gate_decide(0.90)
        assert decision == "proceed"

    def test_confidence_at_threshold_proceeds(self):
        """Confidence equal to sigma gate should return proceed."""
        decision = hc_med_sentinel.sigma_gate_decide(0.88)
        assert decision == "proceed"

    def test_confidence_below_threshold_asks(self):
        """Confidence below sigma gate should return ask."""
        decision = hc_med_sentinel.sigma_gate_decide(0.85)
        assert decision == "ask"

    def test_very_low_confidence_asks(self):
        """Very low confidence should return ask."""
        decision = hc_med_sentinel.sigma_gate_decide(0.30)
        assert decision == "ask"

    def test_custom_threshold(self):
        """Custom threshold should override default."""
        decision = hc_med_sentinel.sigma_gate_decide(0.85, threshold=0.80)
        assert decision == "proceed"

        decision = hc_med_sentinel.sigma_gate_decide(0.85, threshold=0.90)
        assert decision == "ask"


class TestSunHydroSigmaGate:
    """Test sigma gating for hc_sun_hydro skill."""

    def test_sigma_gate_threshold(self):
        """Verify SIGMA_GATE constant is set correctly."""
        assert hc_sun_hydro.SIGMA_GATE == 0.78

    def test_confidence_above_threshold_proceeds(self):
        """Confidence above sigma gate should return proceed."""
        decision = hc_sun_hydro.sigma_gate_decide(0.85)
        assert decision == "proceed"

    def test_confidence_at_threshold_proceeds(self):
        """Confidence equal to sigma gate should return proceed."""
        decision = hc_sun_hydro.sigma_gate_decide(0.78)
        assert decision == "proceed"

    def test_confidence_below_threshold_asks(self):
        """Confidence below sigma gate should return ask."""
        decision = hc_sun_hydro.sigma_gate_decide(0.70)
        assert decision == "ask"

    def test_very_low_confidence_asks(self):
        """Very low confidence should return ask."""
        decision = hc_sun_hydro.sigma_gate_decide(0.15)
        assert decision == "ask"

    def test_custom_threshold(self):
        """Custom threshold should override default."""
        decision = hc_sun_hydro.sigma_gate_decide(0.70, threshold=0.65)
        assert decision == "proceed"

        decision = hc_sun_hydro.sigma_gate_decide(0.70, threshold=0.75)
        assert decision == "ask"


class TestSkillResultDataclass:
    """Test SkillResult dataclass structure."""

    def test_gait_guard_result_structure(self):
        """Verify SkillResult has required fields."""
        result = hc_gait_guard.SkillResult(
            confidence=0.85, prediction="low_risk", metadata={"test": True}
        )
        assert result.confidence == 0.85
        assert result.prediction == "low_risk"
        assert result.metadata == {"test": True}

    def test_med_sentinel_result_structure(self):
        """Verify SkillResult has required fields."""
        result = hc_med_sentinel.SkillResult(
            confidence=0.92, prediction="no_interaction", metadata={"test": True}
        )
        assert result.confidence == 0.92
        assert result.prediction == "no_interaction"
        assert result.metadata == {"test": True}

    def test_sun_hydro_result_structure(self):
        """Verify SkillResult has required fields."""
        result = hc_sun_hydro.SkillResult(
            confidence=0.81, prediction="low_sun_risk", metadata={"test": True}
        )
        assert result.confidence == 0.81
        assert result.prediction == "low_sun_risk"
        assert result.metadata == {"test": True}


class TestRunInferenceStubs:
    """Test that run_inference stubs return valid results."""

    def test_gait_guard_inference(self):
        """Verify gait guard inference returns SkillResult."""
        result = hc_gait_guard.run_inference({"test": "data"})
        assert isinstance(result, hc_gait_guard.SkillResult)
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.prediction, str)
        assert isinstance(result.metadata, dict)

    def test_med_sentinel_inference(self):
        """Verify med sentinel inference returns SkillResult."""
        result = hc_med_sentinel.run_inference({"test": "data"})
        assert isinstance(result, hc_med_sentinel.SkillResult)
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.prediction, str)
        assert isinstance(result.metadata, dict)

    def test_sun_hydro_inference(self):
        """Verify sun hydro inference returns SkillResult."""
        result = hc_sun_hydro.run_inference({"test": "data"})
        assert isinstance(result, hc_sun_hydro.SkillResult)
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.prediction, str)
        assert isinstance(result.metadata, dict)


class TestOnnxExportStubs:
    """Test that ONNX export stubs create placeholder files."""

    def test_gait_guard_export(self, tmp_path):
        """Verify gait guard ONNX export creates file."""
        output = tmp_path / "test_gait.onnx"
        result = hc_gait_guard.export_to_onnx(output_path=output)
        assert result == output
        assert output.exists()
        assert output.read_bytes() == b"ONNX_PLACEHOLDER_hc_gait_guard"

    def test_med_sentinel_export(self, tmp_path):
        """Verify med sentinel ONNX export creates file."""
        output = tmp_path / "test_med.onnx"
        result = hc_med_sentinel.export_to_onnx(output_path=output)
        assert result == output
        assert output.exists()
        assert output.read_bytes() == b"ONNX_PLACEHOLDER_hc_med_sentinel"

    def test_sun_hydro_export(self, tmp_path):
        """Verify sun hydro ONNX export creates file."""
        output = tmp_path / "test_sun.onnx"
        result = hc_sun_hydro.export_to_onnx(output_path=output)
        assert result == output
        assert output.exists()
        assert output.read_bytes() == b"ONNX_PLACEHOLDER_hc_sun_hydro"
