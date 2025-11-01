import numpy as np

from src.perception import get_default_vq


def test_vq_encoder_shape_and_dtype():
    rng = np.random.default_rng(1234)
    frame = rng.random((48, 48, 3), dtype=np.float32)

    encoder = get_default_vq()
    code = encoder.encode(frame)

    assert isinstance(code, np.ndarray)
    assert code.dtype == np.float32
    assert code.shape == (encoder.code_dim,)


def test_vq_encoder_brightness_invariance():
    rng = np.random.default_rng(4321)
    frame = rng.random((32, 32), dtype=np.float32)

    encoder = get_default_vq()
    base_code = encoder.encode(frame)
    shifted_code = encoder.encode(frame + 5.0)

    assert np.allclose(base_code, shifted_code)
