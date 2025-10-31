import numpy as np

from src.perception import get_default_vq


def test_vq_encoder_shape_and_dtype():
    rng = np.random.default_rng(1234)
    frames = rng.random((6, 48, 48, 3)).astype(np.float32)

    encoder = get_default_vq()
    codes = encoder.encode(frames)

    assert isinstance(codes, np.ndarray)
    assert codes.dtype == np.float32
    assert codes.shape == (frames.shape[0], encoder.projection_dim)


def test_vq_encoder_brightness_invariance():
    rng = np.random.default_rng(4321)
    frames = rng.random((4, 32, 32, 3)).astype(np.float32)

    encoder = get_default_vq()
    base_codes = encoder.encode(frames)
    shifted_codes = encoder.encode(frames + 5.0)

    assert np.allclose(base_codes, shifted_codes)
