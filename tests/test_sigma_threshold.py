"""Tests for sigma gate threshold decision logic in health skills."""
from __future__ import annotations

import pytest

# Import sigma gate functions and thresholds from each health skill
from skills.hc_gait_guard import SIGMA_GATE as GAIT_GATE, sigma_gate_decide as gait_decide
from skills.hc_med_sentinel import SIGMA_GATE as MED_GATE, sigma_gate_decide as med_decide
from skills.hc_sun_hydro import SIGMA_GATE as HYDRO_GATE, sigma_gate_decide as hydro_decide


class TestGaitGuardSigmaThreshold:
    """Tests for hc_gait_guard sigma gate threshold."""

    def test_gate_value(self):
        """Verify the sigma gate threshold is set correctly."""
        assert GAIT_GATE == 0.7

    def test_below_threshold_asks(self):
        """Confidence below threshold should return 'ask'."""
        assert gait_decide(0.5) == "ask"
        assert gait_decide(0.69) == "ask"
        assert gait_decide(0.0) == "ask"

    def test_at_threshold_proceeds(self):
        """Confidence at threshold should return 'proceed'."""
        assert gait_decide(0.7) == "proceed"

    def test_above_threshold_proceeds(self):
        """Confidence above threshold should return 'proceed'."""
        assert gait_decide(0.71) == "proceed"
        assert gait_decide(0.85) == "proceed"
        assert gait_decide(1.0) == "proceed"


class TestMedSentinelSigmaThreshold:
    """Tests for hc_med_sentinel sigma gate threshold."""

    def test_gate_value(self):
        """Verify the sigma gate threshold is set correctly."""
        assert MED_GATE == 0.75

    def test_below_threshold_asks(self):
        """Confidence below threshold should return 'ask'."""
        assert med_decide(0.5) == "ask"
        assert med_decide(0.74) == "ask"
        assert med_decide(0.0) == "ask"

    def test_at_threshold_proceeds(self):
        """Confidence at threshold should return 'proceed'."""
        assert med_decide(0.75) == "proceed"

    def test_above_threshold_proceeds(self):
        """Confidence above threshold should return 'proceed'."""
        assert med_decide(0.76) == "proceed"
        assert med_decide(0.90) == "proceed"
        assert med_decide(1.0) == "proceed"


class TestSunHydroSigmaThreshold:
    """Tests for hc_sun_hydro sigma gate threshold."""

    def test_gate_value(self):
        """Verify the sigma gate threshold is set correctly."""
        assert HYDRO_GATE == 0.65

    def test_below_threshold_asks(self):
        """Confidence below threshold should return 'ask'."""
        assert hydro_decide(0.5) == "ask"
        assert hydro_decide(0.64) == "ask"
        assert hydro_decide(0.0) == "ask"

    def test_at_threshold_proceeds(self):
        """Confidence at threshold should return 'proceed'."""
        assert hydro_decide(0.65) == "proceed"

    def test_above_threshold_proceeds(self):
        """Confidence above threshold should return 'proceed'."""
        assert hydro_decide(0.66) == "proceed"
        assert hydro_decide(0.80) == "proceed"
        assert hydro_decide(1.0) == "proceed"


class TestSigmaThresholdComparison:
    """Tests comparing sigma thresholds across skills."""

    def test_thresholds_ordered_correctly(self):
        """Verify skills have appropriate threshold ordering."""
        # hc_sun_hydro should have lowest threshold (most lenient)
        # hc_gait_guard should be moderate
        # hc_med_sentinel should have highest threshold (most strict)
        assert HYDRO_GATE < GAIT_GATE < MED_GATE
        assert HYDRO_GATE == 0.65
        assert GAIT_GATE == 0.7
        assert MED_GATE == 0.75

    def test_all_thresholds_in_valid_range(self):
        """All thresholds should be between 0 and 1."""
        for gate in [HYDRO_GATE, GAIT_GATE, MED_GATE]:
            assert 0.0 <= gate <= 1.0
