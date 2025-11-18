"""RaySkillKit runtime helpers that respect wearable duty cycles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol

import numpy as np

from controls.duty_cycle import DutyCycleScheduler
from fsm import HandshakeFSM, HandshakeState
from src.perception.vision_keyframe import frames_from_camera


class CameraProvider(Protocol):
    """Protocol exposing the camera generator used by RaySkillKit."""

    def camera(self, *, seconds: int = 1) -> Iterable[np.ndarray]:  # pragma: no cover - protocol
        ...


class OrtWrapper(Protocol):
    """Minimal protocol for ONNX Runtime wrappers used by RaySkillKit."""

    def infer(self, model_name: str, features: np.ndarray) -> np.ndarray:  # pragma: no cover
        ...


@dataclass
class RaySkillKitRuntime:
    """Entry point that gates camera + inference work by engagement state."""

    handshake: HandshakeFSM
    scheduler: DutyCycleScheduler
    channel: str = "vision"

    def __post_init__(self) -> None:
        self.scheduler.bind(self.handshake)

    def capture_clip(self, provider: CameraProvider, *, seconds: int = 1) -> np.ndarray | None:
        """Capture a camera clip if permitted by the duty-cycle budget."""

        if self.handshake.state is not HandshakeState.READY:
            return None
        if not self.scheduler.try_acquire(self.channel):
            return None
        clip = frames_from_camera(provider, seconds=seconds)
        return clip

    def run_inference(
        self, ort: OrtWrapper, skill_id: str, features: np.ndarray, *, channel: str | None = None
    ) -> np.ndarray | None:
        """Invoke ``OrtWrapper.infer`` when the duty-cycle allows it."""

        if self.handshake.state is not HandshakeState.READY:
            return None
        gate = channel or self.channel
        if not self.scheduler.try_acquire(gate):
            return None
        result = ort.infer(skill_id, features)
        return result
