"""Production-grade driver implementations for Meta hardware.

These implementations are intentionally resilient: they attempt to use
available hardware (camera, microphone, speakers, etc.) but gracefully
degrade when a device or dependency is missing. The goal is to keep the
interface surface identical to the mock provider while exercising real
side effects when the environment supports them.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import time
from typing import Iterator

import numpy as np

from ..interfaces import AudioOut, CameraIn, DisplayOverlay, Haptics, MicIn, Permissions
from .base import ProviderBase

try:  # Optional dependency used for camera and overlay rendering
    import cv2
except Exception:  # pragma: no cover - best-effort optional import
    cv2 = None  # type: ignore

try:  # Optional dependency used for microphone capture
    import sounddevice as sd
except Exception:  # pragma: no cover - best-effort optional import
    sd = None  # type: ignore

try:  # Optional dependency used for microphone capture fallback
    import pyaudio
except Exception:  # pragma: no cover - best-effort optional import
    pyaudio = None  # type: ignore

try:  # Optional dependency used for TTS
    import pyttsx3
except Exception:  # pragma: no cover - best-effort optional import
    pyttsx3 = None  # type: ignore


LOGGER = logging.getLogger(__name__)
_DEFAULT_COLOR = (0, 255, 0)


class MetaCameraIn(CameraIn):
    """Stream frames from a connected camera device using OpenCV."""

    def __init__(self, device_index: int = 0, fps: float = 30.0) -> None:
        self._device_index = device_index
        self._fps = fps

    def get_frames(self) -> Iterator[np.ndarray]:  # type: ignore[override]
        if cv2 is None:  # pragma: no cover - dependent on optional hardware
            LOGGER.warning("OpenCV is not available; camera streaming is disabled")
            return
        cap = cv2.VideoCapture(self._device_index)
        if not cap.isOpened():
            LOGGER.warning("Camera device %s could not be opened", self._device_index)
            cap.release()
            return

        delay = 1.0 / max(self._fps, 0.1)
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    LOGGER.warning("Failed to read frame from camera device %s", self._device_index)
                    break
                yield frame
                time.sleep(delay)
        finally:
            cap.release()


class MetaMicIn(MicIn):
    """Capture audio frames from the default microphone input."""

    def __init__(
        self,
        sample_rate_hz: int = 16000,
        frame_size: int = 1024,
        channels: int = 1,
    ) -> None:
        self._sample_rate_hz = sample_rate_hz
        self._frame_size = frame_size
        self._channels = channels

    def _stream_with_sounddevice(self) -> Iterator[np.ndarray]:
        if sd is None:
            return iter(())

        try:
            stream = sd.InputStream(
                samplerate=self._sample_rate_hz,
                channels=self._channels,
                blocksize=self._frame_size,
                dtype="float32",
            )
        except Exception as exc:  # pragma: no cover - runtime hardware failure
            LOGGER.warning("Unable to open sounddevice input stream: %s", exc)
            return iter(())

        stream.__enter__()
        LOGGER.info("Microphone capture started via sounddevice")
        try:
            while True:
                data, overflowed = stream.read(self._frame_size)
                if overflowed:
                    LOGGER.warning("Microphone input overflow detected")
                yield np.asarray(data, dtype=np.float32)
        except Exception as exc:  # pragma: no cover - runtime hardware failure
            LOGGER.warning("Microphone capture stopped due to error: %s", exc)
        finally:
            stream.__exit__(None, None, None)
            LOGGER.info("Microphone capture stopped")

    def _stream_with_pyaudio(self) -> Iterator[np.ndarray]:
        if pyaudio is None:
            return iter(())

        audio = pyaudio.PyAudio()
        try:
            stream = audio.open(
                format=pyaudio.paFloat32,
                channels=self._channels,
                rate=self._sample_rate_hz,
                input=True,
                frames_per_buffer=self._frame_size,
            )
        except Exception as exc:  # pragma: no cover - runtime hardware failure
            LOGGER.warning("Unable to open PyAudio input stream: %s", exc)
            audio.terminate()
            return iter(())

        LOGGER.info("Microphone capture started via PyAudio")
        try:
            while True:
                buffer = stream.read(self._frame_size, exception_on_overflow=False)
                frame = np.frombuffer(buffer, dtype=np.float32)
                yield frame.reshape(-1, self._channels)
        except Exception as exc:  # pragma: no cover - runtime hardware failure
            LOGGER.warning("Microphone capture stopped due to error: %s", exc)
        finally:
            stream.stop_stream()
            stream.close()
            audio.terminate()
            LOGGER.info("Microphone capture stopped")

    def get_frames(self) -> Iterator[np.ndarray]:  # type: ignore[override]
        if sd is not None:
            yield from self._stream_with_sounddevice()
            return
        if pyaudio is not None:
            yield from self._stream_with_pyaudio()
            return
        LOGGER.warning("No audio input backend available; microphone is disabled")
        return iter(())


class MetaAudioOut(AudioOut):
    """Use a local TTS engine (pyttsx3) to synthesize speech."""

    def __init__(self) -> None:
        self._engine = None
        self._utterance_index = 0

    def _ensure_engine(self) -> bool:
        if self._engine is not None:
            return True
        if pyttsx3 is None:
            LOGGER.warning("pyttsx3 is not available; speech synthesis disabled")
            return False
        try:
            self._engine = pyttsx3.init()
            return True
        except Exception as exc:  # pragma: no cover - runtime environment specific
            LOGGER.warning("Unable to initialize TTS engine: %s", exc)
            self._engine = None
            return False

    def speak(self, text: str) -> dict:
        if not self._ensure_engine():
            return {"text": text, "status": "unavailable"}

        utterance_index = self._utterance_index
        self._utterance_index += 1
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        try:
            assert self._engine is not None
            self._engine.say(text)
            self._engine.runAndWait()
            status = "spoken"
        except Exception as exc:  # pragma: no cover - runtime environment specific
            LOGGER.warning("TTS playback failed: %s", exc)
            status = "error"

        return {
            "text": text,
            "utterance_index": utterance_index,
            "timestamp": timestamp,
            "status": status,
        }


class MetaDisplayOverlay(DisplayOverlay):
    """Draw captions or bounding boxes on an input frame."""

    def __init__(self, font_scale: float = 0.6, thickness: int = 2) -> None:
        self._font_scale = font_scale
        self._thickness = thickness

    def render(self, card: dict) -> dict:
        if cv2 is None:  # pragma: no cover - dependent on optional hardware
            LOGGER.warning("OpenCV is not available; overlay rendering is disabled")
            return {"card": card, "status": "unavailable"}

        frame = card.get("frame") if isinstance(card, dict) else None
        if frame is None:
            frame = np.zeros((480, 640, 3), dtype=np.uint8)

        rendered = frame.copy()
        caption = card.get("caption") if isinstance(card, dict) else None
        if caption:
            cv2.putText(
                rendered,
                str(caption),
                (10, rendered.shape[0] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                self._font_scale,
                _DEFAULT_COLOR,
                self._thickness,
                cv2.LINE_AA,
            )

        for box in card.get("boxes", []) if isinstance(card, dict) else []:
            x1, y1, x2, y2 = box.get("x1", 0), box.get("y1", 0), box.get("x2", 0), box.get("y2", 0)
            label = box.get("label")
            cv2.rectangle(rendered, (int(x1), int(y1)), (int(x2), int(y2)), _DEFAULT_COLOR, self._thickness)
            if label:
                cv2.putText(
                    rendered,
                    str(label),
                    (int(x1), max(0, int(y1) - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    self._font_scale,
                    _DEFAULT_COLOR,
                    self._thickness,
                    cv2.LINE_AA,
                )

        return {"card": card, "rendered_frame": rendered, "status": "rendered"}


class MetaHaptics(Haptics):
    """Trigger wearable vibrations or simulate them via logging."""

    def vibrate(self, ms: int) -> None:
        LOGGER.info("Haptics vibrate for %sms", ms)
        time.sleep(max(ms, 0) / 1000.0)

    def buzz(self, ms: int) -> None:
        """Alias for vibrate to mimic device API surface."""
        self.vibrate(ms)


class MetaPermissions(Permissions):
    """Best-effort permissions broker that accepts provided capabilities."""

    def request(self, capabilities: set[str]) -> dict:  # noqa: D401 - documented in interface
        requested = sorted(capabilities)
        response = {
            "requested": requested,
            "granted": requested,
            "denied": [],
            "status": "granted",
        }
        LOGGER.info("Permissions granted for capabilities: %s", ", ".join(requested))
        return response


class MetaProvider(ProviderBase):
    """Aggregate of production driver placeholders."""

    def __init__(
        self,
        *,
        camera_device_index: int = 0,
        camera_fps: float = 30.0,
        microphone_sample_rate_hz: int = 16000,
        microphone_frame_size: int = 1024,
        microphone_channels: int = 1,
        overlay_font_scale: float = 0.6,
        overlay_thickness: int = 2,
        **kwargs,
    ) -> None:
        self._camera_device_index = camera_device_index
        self._camera_fps = camera_fps
        self._microphone_sample_rate_hz = microphone_sample_rate_hz
        self._microphone_frame_size = microphone_frame_size
        self._microphone_channels = microphone_channels
        self._overlay_font_scale = overlay_font_scale
        self._overlay_thickness = overlay_thickness
        super().__init__(**kwargs)

    def _create_camera(self) -> CameraIn | None:
        return MetaCameraIn(device_index=self._camera_device_index, fps=self._camera_fps)

    def _create_microphone(self) -> MicIn | None:
        return MetaMicIn(
            sample_rate_hz=self._microphone_sample_rate_hz,
            frame_size=self._microphone_frame_size,
            channels=self._microphone_channels,
        )

    def _create_audio_out(self) -> AudioOut | None:
        return MetaAudioOut()

    def _create_overlay(self) -> DisplayOverlay | None:
        return MetaDisplayOverlay(font_scale=self._overlay_font_scale, thickness=self._overlay_thickness)

    def _create_haptics(self) -> Haptics | None:
        return MetaHaptics()

    def _create_permissions(self) -> Permissions | None:
        return MetaPermissions()


__all__ = [
    "MetaAudioOut",
    "MetaCameraIn",
    "MetaDisplayOverlay",
    "MetaHaptics",
    "MetaMicIn",
    "MetaPermissions",
    "MetaProvider",
]
