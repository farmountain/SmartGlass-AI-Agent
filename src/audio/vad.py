"""Audio compatibility layer re-exporting the perception VAD implementation."""

from __future__ import annotations

from perception.vad import EnergyVAD

__all__ = ["EnergyVAD"]
