# SDK Readiness Checklist

This note summarizes the DAL/provider surface, RaySkillKit bundle coverage, verification steps for signing and hot updates, and the minimum guardrails required before shipping.

## DAL providers and mocks
- **`mock` (default)** – Offline camera/mic fixtures used by CI and examples.
- **`meta` SDK wrapper** – Delegates to the Meta Ray-Ban SDK when `metarayban` is importable **and** `prefer_sdk=True`, otherwise emits deterministic mock telemetry that mirrors the expected schema. Configurable fields: `api_key`, `device_id`, and `transport`.【F:README.md†L72-L110】
- **Vendor mocks** – Deterministic fixtures for `vuzix` (640x480 RGB + waveguide overlays), `xreal` (1080p Beam-style captures + Nebula overlays), `openxr` (square eye buffers + host delegated overlays), and `visionos` (1440x1440 persona frames + shared-space overlays).【F:README.md†L112-L139】

## RaySkillKit skill bundle coverage
- Twelve skills are present in the catalogue packaged with the pilot drop: `skill_001`, `skill_002`, `skill_003`, `travel_fastlane`, `travel_safebubble`, `travel_bargaincoach`, `retail_wtp_radar`, `retail_capsule_gaps`, `retail_minute_meal`, `rt_wtp_radar`, `rt_capsule_gaps`, and `rt_minute_meal`.【F:README.md†L99-L114】
- Travel models are generated on demand by CI; retail INT8 exports and stats are versioned under `rayskillkit/skills/{models,stats}/retail` to keep regression runs deterministic.【F:README.md†L116-L117】

## Signing and hot-update verification
- **Pilot drop signing** – Use `cicd/package_release.py` with an Ed25519 seed (`--key` or `--key-env`) to emit `release_manifest.json` plus `release_manifest.sig`; tagged pushes run the same signer in CI so artifacts can be validated before distribution.【F:README.md†L118-L139】
- **Hot-update handling** – Cost modeling tracks hot-update overhead alongside DAL and compute costs for every scenario; keep cost deltas within the guardrails used in the comparison sheet when enabling over-the-air refreshes.【F:docs/cost_model_README.md†L24-L35】

## Performance and safety KPIs
- **Perf benches** –
  - `python bench/audio_bench.py --out artifacts/audio_latency.csv` captures VAD/ASR frame latency and reversal stability on deterministic signals.【F:README.md†L145-L156】
  - `python bench/image_bench.py` records keyframe/encoder timings and OCR mock precision into `artifacts/image_latency.csv` and `artifacts/ocr_results.csv`.【F:README.md†L158-L168】
- **Safety (red-team) runs** – Execute `python redteam/eval.py --scenarios redteam/health.yaml --out artifacts/redteam_report.json` to ensure allow/deny decisions match expectations for self-harm and cardiac prompts before release.【F:redteam/eval.py†L10-L95】【F:redteam/health.yaml†L1-L20】

## Required checklist (integration guardrails)
- DAL provider coverage validated across `mock`, `meta`, and vendor mocks; parity issues block release.
- Provider mocks exercised in CI to ensure overlays and permissions match guardrail expectations.【F:docs/WEEK_01.md†L72-L95】
- Hot-update path costed and monitored against comparison-sheet guardrails.【F:docs/cost_model_README.md†L24-L35】
- Pilot drop manifest signed and signature verified prior to distribution.【F:README.md†L118-L139】
- Red-team suite passes for health and safety scenarios before rollout.【F:redteam/eval.py†L10-L95】【F:redteam/health.yaml†L1-L20】
- Performance study completed with latest audio and image bench artifacts; p95 latency must remain under the weekly 95 ms target used in integration reviews.【F:README.md†L145-L168】【F:docs/WEEK_04.md†L39-L41】

## Acceptance criteria
- All checklist items above are green with artifacts (bench CSVs, red-team report, signed manifest) attached to the release candidate.
- Integration guardrails from the perception/overlay pipeline remain satisfied—mobile fallback stays in lockstep with headset overlays when `has_display()` is false, and provider swap exercises do not regress recorded acceptance tests.【F:docs/WEEK_03.md†L23-L65】
