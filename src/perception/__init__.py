"""Perception utilities for keyframing and vector quantization."""

from .vision_keyframe import VQEncoder, select_keyframes


def get_default_keyframer():
    """Return the default keyframe selection callable."""

    return select_keyframes


def get_default_vq(seed: int | None = None) -> VQEncoder:
    """Return the default vector-quantizer encoder instance.

    Parameters
    ----------
    seed:
        Optional override for the deterministic encoder seed. When ``None`` the
        module default is used.
    """

    return VQEncoder(seed=seed)


__all__ = ["get_default_keyframer", "get_default_vq", "select_keyframes", "VQEncoder"]
