# Week 3 Report

## Goals
- Finalise deterministic frame-difference keyframe selection and document the tuning surface for wearable video capture.
- Lock in vector-quantised (VQ) encoding stubs so downstream retrieval experiments remain reproducible without GPU codecs.
- Define the OCR interchange schema, opt-in engine toggles, and privacy guardrails shared by the vision subsystem.
- Add an image benchmark that complements the audio bench with keyframe, encoding, and OCR quality signals.

## Exit Criteria
- Frame-diff parameters (`diff_tau`, `min_gap`) explained with invariances, failure cases, and data-guided defaults.
- VQ encoder stub behaviour described for anyone swapping in hardware accelerators later.
- OCR schema, engine-selection rules, and privacy posture documented with deterministic fallbacks.
- New image benchmark interpreted so contributors know how to read telemetry and CSV artifacts.

## Frame-Diff Keyframe Design
`select_keyframes` down-samples each frame into an 8×8 grid before computing L2 diffs, which keeps runtime bounded on-device and reduces dependence on raw resolution.【F:src/perception/vision_keyframe.py†L12-L65】 Two parameters govern behaviour:

- `diff_tau`: the accumulated L2 threshold that must be exceeded before accepting another keyframe. Defaults (6–8) assume 64×64 synthetic feeds; values scale with scene contrast and desired sensitivity.
- `min_gap`: the minimum frame distance between accepted keyframes, preventing rapid toggling when motion jitter sits above the threshold.

The down-sampling step yields invariance to modest scale changes and colour permutations because channel averages are taken before pooling, but it is still sensitive to global illumination spikes. Failure modes include:

- Sudden full-frame exposure swings (e.g., automatic gain control) that trigger false positives because the global L2 exceeds `diff_tau`.
- Localised high-frequency noise (sensor sparkle) that accumulates slowly and could block legitimate keyframes unless `min_gap` is relaxed.
- Clips that start mid-action, where the first frame does not capture the true baseline, making the final keyframe redundant; forcing the last frame ensures coverage but may duplicate content.

To mitigate these cases we document practical heuristics: lower `diff_tau` for low-light sensors, raise it with aggressive optical stabilisation, and ratchet `min_gap` downward only when the sensor pipeline already handles noise. Contributors swapping to higher-resolution sources should recompute the implicit `scale` term (area ratio between originals and down-sampled grids) to keep thresholds meaningful.【F:src/perception/vision_keyframe.py†L38-L61】

## VQ Encoder Stub Behaviour
`VQEncoder` seeds a deterministic RNG, projects the flattened 8×8 grids into a configurable latent dimension, and selects the nearest centroid from a static codebook.【F:src/perception/vision_keyframe.py†L67-L116】 Because both the projection matrix and codebook derive from the seed, runs are fully reproducible and portable. The stub intentionally avoids SIMD or GPU paths while still emitting embeddings that downstream retrieval or captioning code can consume.

Operational guidance:

- Treat the projection dimension (`projection_dim=16`) as the stand-in for hardware codecs; larger dimensions increase CSV sizes but remain deterministic.
- Codebook indices are implicit—the encoder returns centroids rather than IDs to avoid coupling to any specific VQ-VAE implementation. Integrators targeting NVIDIA or Hexagon hardware can reinterpret those vectors as logits for their accelerators while keeping the offline stub for CI.
- Empty keyframe lists produce zero-length embeddings, signalling "no motion" clips without raising.

## OCR Schema and Engine Swapping
The OCR layer exposes a uniform schema: `{"text": str, "boxes": Tuple[BBox, ...], "conf": Tuple[float, ...], "by_word": Tuple[Dict, ...]}` where each `by_word` entry holds `{"text", "box", "conf"}`.【F:src/perception/ocr.py†L13-L63】 `MockOCR` fabricates detections by thresholding bright rectangles, making it fully offline yet faithful to the production interface.

Engine selection hangs off environment flags. Setting `USE_EASYOCR=1` or `USE_TESSERACT=1` currently raises explicit runtime errors in offline contexts, prompting developers to supply the real backends when running on provisioned devices.【F:src/perception/ocr.py†L65-L78】 Swapping engines therefore means:

1. Implement the real backend with the same return schema.
2. Gate it behind the corresponding environment flag.
3. Leave `MockOCR` as the default so CI and local testing stay credential-free.

## Privacy Guarantees
Vision privacy mirrors the audio defaults: everything stays offline and deterministic unless explicitly toggled. `DeterministicRedactor` masks anchor regions (top-left for faces, bottom-right for plates) before any downstream logging and returns a structured `RedactionSummary` for telemetry.【F:privacy/redact.py†L1-L89】 Combined with `MockOCR`’s synthetic detections and the frame-diff pipeline, Week 3 guarantees that the new image benchmark never emits raw user imagery. Contributors deploying real OCR engines must keep the same redaction pre-processing and audit the environment flags in review.

## Image Bench Interpretation
`bench/image_bench.py` synthesises three clip archetypes (static, gradient, motion), runs keyframe selection followed by VQ encoding, and writes timing/keyframe counts to `artifacts/image_latency.csv` under deterministic seeds.【F:bench/image_bench.py†L1-L103】 It also fabricates a dual-panel scene to evaluate OCR precision, exporting metrics such as `expected_panels`, `matched_panels`, and `latency_ms` to `artifacts/ocr_results.csv`.【F:bench/image_bench.py†L105-L175】 CI surfaces those CSVs alongside telemetry counters (`vision.keys_rate`, `ocr.precision_synth`), letting reviewers spot regressions in keyframe density or OCR recall without relying on proprietary footage.

When reading the bench outputs:

- Compare `keyframes` across clip types to ensure `diff_tau` thresholds track motion correctly (e.g., `static` should stay at two keyframes: first and last).
- Inspect `vision.keys_rate` to verify per-frame reduction ratios remain stable if frame rates change.
- Use `ocr.precision_synth` as a guardrail—values below 1.0 imply the mock detector is dropping panels, often due to threshold changes.

## Retro (Paul-Elder + Inversion)
- *Paul–Elder Critical Thinking*: Claims about keyframe robustness now cite deterministic benchmarks, explicit parameters, and telemetry artifacts, while acknowledging vulnerabilities like exposure swings. Assumptions (8×8 pooling, synthetic clips) and implications (CI-only reproducibility) are spelled out so reviewers can challenge them with empirical diffs.
- *Inversion*: If we inverted the posture—allowing nondeterministic codecs or cloud OCR—the bench would leak real imagery, telemetry would fluctuate, and debugging would depend on credentials. Designing the stubbed VQ path and MockOCR with this inversion in mind kept privacy and reproducibility non-negotiable.
