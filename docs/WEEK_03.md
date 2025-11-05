# Week 3 Notes

## Keyframe & VQ Algorithm Notes
- The keyframe generator now operates on variable-length windows with adaptive thresholds tuned during week 3 experiments.
- VQ (Vector Quantization) embeddings are produced for each retained keyframe; the codebook is kept fixed across runs to preserve comparability between mock and production data.
- When consecutive frames diverge below the similarity threshold, we enforce a minimum dwell before selecting the next keyframe to avoid rapid oscillations.

## Parameter Reference
- `diff_tau`: Controls the minimum per-channel difference required before a frame is considered a candidate keyframe. Lower values make the detector more sensitive but increase false positives.
- `min_gap`: Specifies the minimum number of frames between accepted keyframes to ensure temporal spacing. This replaces the earlier `min_stride` constant.
- Default values were established using the week 3 regression suite; adjust only after verifying parity against the reference CSV baselines.

## Invariances and Failure Modes
- Invariance: The pipeline is insensitive to uniform brightness shifts due to histogram normalization before diffing.
- Invariance: Rotational invariance up to ±5° is achieved through the new affine alignment pre-pass.
- Failure Mode: Fast scene cuts that exceed the `min_gap` spacing can be missed; mitigate by temporarily reducing `min_gap`.
- Failure Mode: High-frequency noise (rain, scanlines) can prematurely trigger `diff_tau`; the recommended mitigation is to increase the temporal smoothing window to 5 frames.

## OCR Interface (Mock vs. Real)
- Mock OCR: Uses the `ocr.mock.OCRClient` which returns deterministic text snippets from fixtures; ideal for CI and unit tests.
- Real OCR: Implemented via `ocr.azure.AzureOCRClient`; requires network credentials and is disabled in CI by default.
- Switch between them using the `OCR_PROVIDER` environment variable (`mock`|`azure`).
- When running benchmarks, ensure the chosen provider is recorded in the metadata column of the CSV outputs.

## Overlay vs. Phone Parity Rule
- Overlays rendered in the headset must match the mobile companion view within a single frame of latency.
- Any new overlay layout must be verified on both devices; if discrepancies are found, the overlay deployment is blocked until parity is restored.
- Use the parity regression harness (`scripts/check_overlay_parity.py`) before shipping layout changes.

## Privacy Stance
- No images or raw video frames may leave the device or CI environment.
- Only derived metadata (embeddings, keyframe indices, and OCR text) can be exported.
- All third-party integrations must run locally or within approved privacy-preserving sandboxes.

## Reading the Week 3 CSVs
- CSV files now include the columns: `timestamp_ms`, `keyframe_id`, `vq_bucket`, `ocr_text`, `ocr_provider`, and `notes`.
- `timestamp_ms`: Milliseconds since capture start.
- `keyframe_id`: Sequential identifier aligned with the new `min_gap` rule.
- `vq_bucket`: Index into the shared codebook for quick clustering.
- `ocr_text`: Text returned by the selected OCR provider; mock outputs will be prefixed with `[MOCK]`.
- `ocr_provider`: Records whether `mock` or `azure` OCR was used for the run.
- `notes`: Freeform annotations; use this to document parameter overrides or observed anomalies.
- Load CSVs with pandas using `parse_dates=False` and `dtype={'keyframe_id': int}` to keep identifiers stable.

## Retro: Paul-Elder + Inversion

### Purpose
- Capture lessons from week 3 perception + OCR workstreams and connect them to the guard-rails enforced by the CI suites (`tests/test_keyframes_rate.py`, `tests/test_vq_code_shape.py`, `tests/test_keyframes_provider_contract.py`, `tests/test_ocr_schema.py`, `tests/test_ocr_mock_panels.py`, `tests/test_ocr_overlay_parity.py`, `tests/test_perception_factories.py`).

### Key Questions
- Are we explicit about the goals and acceptance criteria for keyframe density, VQ embeddings, and OCR overlays?
- Do the mock implementations still exercise the same user journeys as the HUD + phone pairing?
- Where do the invariants in CI map to field hypotheses (e.g., minimum gap vs. missed events)?

### Information
- CI dashboards: [Keyframes](https://ci.internal/keyframes-week3), [VQ](https://ci.internal/vq-week3), [OCR Parity](https://ci.internal/ocr-parity-week3).
- Reference diff thresholds (`diff_tau`) and `min_gap` defaults are stored in the perception factory helpers and are validated by the regression tests listed above.
- Overlay parity traces live in `scripts/check_overlay_parity.py`; the mock suite replays the same fixtures to catch divergence early.

### Inferences
- τ / `min_gap` tuning: Tightening `diff_tau` without relaxing `min_gap` results in under-sampling fast motion; CI catches this via `test_keyframes_rate.py` and `test_keyframes_provider_contract.py`.
- Display parity: Passing `test_ocr_overlay_parity.py` implies that HUD + phone payloads remain byte-for-byte identical for a given OCR result, so UI regressions surface before release.

### Inversion Check
- If the HUD display path drops frames or is unavailable, the phone companion experience must still satisfy every acceptance test. The mocks emulate this by routing through the phone card path even when `has_display()` is false, ensuring parity obligations are met.
