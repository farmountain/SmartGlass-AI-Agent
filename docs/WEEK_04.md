# Week 4 – Fusion α(t), FSM, and Hero-1 Latency

## Fusion α(t) Schedule and Smoothing
We parameterise the audio/vision blend with an adaptive gate α(t) derived from the relative modality confidences:

\[
\alpha_{\text{raw}}(t) = \sigma\big(k \cdot (c_v(t) - c_a(t)) + b\big)
\]

where `σ` is the numerically stable logistic function, `k` controls transition steepness, and `b` shifts the midpoint.【F:src/fusion/gate_mi.py†L10-L44】 The raw value feeds an exponential smoother so that abrupt modality swings do not thrash downstream policies:

\[
\alpha(t) = (1-\beta)\,\alpha(t-1) + \beta\,\alpha_{\text{raw}}(t), \quad \beta \in [0,1]
\]

with bounds enforcement to keep α(t) ∈ [0,1].【F:src/fusion/gate_mi.py†L45-L88】 Small β (e.g., 0.25) privileges temporal stability, while larger β lets fast-changing sensors steer the blend quickly. As the vision confidence `c_v` rises relative to audio `c_a`, α(t) approaches 1.0 and the fusion output emphasises the visual signal; when audio confidence dominates, α(t) decays toward 0.0, biasing the policy toward speech cues. Equal confidences converge to α(t) ≈ 0.5 after the smoother settles, ensuring symmetric weighting.

## Interaction FSM (ASCII)
```
+-------+   activate    +-----------+   observe    +------------+
| IDLE  | ----------->  | LISTENING | ---------->  | ANALYSING  |
+-------+               +-----------+              +------------+
     ^                       |   respond(confirm)          |
     |                       v                             v
     +------------------  +-----------+  <---------------+
                          | RESPONDING|
                          +-----------+
```
The router instantiates four states (`IDLE`, `LISTENING`, `ANALYSING`, `RESPONDING`) with irreversible completion once the caption is emitted, mirroring the guardrails in the hero caption pipeline.【F:examples/hero1_caption.py†L189-L239】

## Hero-1 End-to-End Flow
1. **Provider I/O bootstrap** – Resolve the wearable provider, capture metadata, and set up audio/display capabilities.【F:examples/hero1_caption.py†L226-L277】
2. **Perception** – Synthesise the evaluation clip and audio, run VAD and ASR to obtain speech ratio and transcript candidates, and extract visual keyframes.【F:examples/hero1_caption.py†L202-L261】
3. **Fusion** – Map VAD/keyframe confidences into modality signals, evaluate the fusion gate, and update α(t) diagnostics before publishing blended scores and latency telemetry.【F:examples/hero1_caption.py†L262-L279】【F:src/fusion/gate_mi.py†L31-L88】
4. **Policy** – Step the FSM router through activation, observation, and response transitions, guaranteeing a single outbound reply per activation window.【F:examples/hero1_caption.py†L240-L256】
5. **Outputs** – Generate the caption, hand it to the provider’s audio/display channels, and record overlay rendering plus total runtime for CI inspection.【F:examples/hero1_caption.py†L280-L318】

## Latency Budget and CI Aggregates
Weekly targets hold the end-to-end hero path under 95 ms (p95). Continuous integration captures 20-run aggregates using the synthetic scenario; the latest summary is below.【F:docs/artifacts/week_04_e2e_hero1_summary.json†L1-L47】

| Stage | Target p95 (ms) | Observed p50 (ms) | Observed p95 (ms) |
| --- | --- | --- | --- |
| synth_clip_ms | ≤ 5 | 0.339 | 1.790 |
| synth_audio_ms | ≤ 5 | 0.228 | 0.936 |
| vad_ms | ≤ 6 | 3.529 | 4.510 |
| asr_ms | ≤ 5 | 0.120 | 0.438 |
| keyframe_ms | ≤ 40 | 31.755 | 34.980 |
| fusion_audio_ms | ≤ 1 | 0.007 | 0.009 |
| fusion_vision_ms | ≤ 1 | 0.001 | 0.001 |
| fusion_gate_ms | ≤ 1 | 0.026 | 0.037 |
| fsm_ms | ≤ 2 | 0.005 | 0.009 |
| caption_ms | ≤ 55 | 43.512 | 48.493 |
| tts_ms | ≤ 8 | 1.249 | 1.534 |
| **total** | **≤ 95** | **80.910** | **90.670** |

CI stores both raw stage timings and fused-score statistics (`score_mean` = 0.659), giving reviewers early warning if α(t) drifts toward a modality lockout.【F:docs/artifacts/week_04_e2e_hero1_summary.json†L35-L47】

## Privacy Note
Hero-1 validation remains fully synthetic: clips, speech, and overlays are generated offline, and any downstream frame logging still routes through the deterministic redaction stub before persistence. No real user data is processed in CI or shared artifacts.【F:examples/hero1_caption.py†L202-L318】【F:privacy/redact.py†L1-L75】

## Retro – Paul-Elder + Inversion
**Purpose** – Capture week-four learning loops so that future Hero-1 reviews have a single reference for the α(t) gate, FSM behaviour, and latency tooling.【F:src/fusion/gate_mi.py†L10-L94】【F:examples/hero1_caption.py†L230-L348】

**Questions at issue** – Where do α(t) drift risks originate, and how do we maintain FSM guarantees while respecting the 95 ms latency envelope?【F:src/fusion/gate_mi.py†L10-L94】【F:examples/hero1_caption.py†L274-L348】

**Evidence** – Provider-backed E2E CSV timings plus the CI summary confirm that fusion, captioning, and overlay paths remain within budget (`total_p95` = 90.670 ms).【F:docs/artifacts/week_04_e2e_hero1.csv†L1-L13】【F:docs/artifacts/week_04_e2e_hero1_summary.json†L1-L52】

**Inferences** – β tuning and `min_gap` spacing jointly stabilise α(t): increasing β when modality gaps are sparse recovers responsiveness, while widening `min_gap` suppresses frame spam without starving the overlay.【F:src/fusion/gate_mi.py†L45-L94】【F:examples/hero1_caption.py†L258-L318】

**Implications** – Before committing adjustments, validate via provider confirm signals so the FSM does not emit duplicate speech/actions under latency stress.【F:examples/hero1_caption.py†L274-L318】【F:tests/test_fsm_confirm_required.py†L1-L59】

**Inversion** – If latency regresses, audit keyframe density and reduce β or raise `min_gap`; if overlays vanish, remember the phone card parity invariant still holds, so validate parity handlers before touching fusion heuristics.【F:docs/artifacts/week_04_e2e_hero1_summary.json†L1-L52】【F:examples/hero1_caption.py†L288-L318】【F:tests/test_speak_overlay_parity.py†L1-L63】
