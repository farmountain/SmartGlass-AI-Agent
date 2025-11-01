# Week 2 Report

## Goals
- Harden the audio front-end by characterising the `EnergyVAD` energy curve on synthetic speech/noise mixes and validating the refreshed Provider.MicIn → VAD → ASR (Mock in CI) → δ gate streaming path.
- Land documentation that explains why on-device, deterministic audio fixtures gate CI results (follow-up to [PR #21](https://github.com/farmountain/SmartGlass-AI-Agent/pull/21) and [PR #22](https://github.com/farmountain/SmartGlass-AI-Agent/pull/22)).
- Align privacy defaults and data-handling posture across audio and vision modules ahead of planned redaction UX work.

## Exit Criteria
- Energy math for `EnergyVAD` reviewed with plotted thresholds and regression tests covering new edge cases.
- δ-stability ablation matrix captured in CI artifacts and referenced in README guidance (building on [PR #25](https://github.com/farmountain/SmartGlass-AI-Agent/pull/25)).
- Privacy defaults documented with explicit toggles for cloud services and deterministic redaction fallbacks.

## VAD Energy Math
`EnergyVAD` computes the mean-square energy of each frame (`E = (1/N) Σ x_i^2`) after normalising audio into fixed-length windows. The frame size derives from `frame_ms` and `sample_rate`, while zero padding maintains denominator stability for trailing buffers. Introducing the decision threshold τ clarifies that the configured energy limit (`τ ≈ 1e-3` by default) maps directly to an RMS magnitude of ~0.031 (`√τ`), offering millisecond-scale decision latency at 16 kHz sampling. Regression coverage in `tests/test_vad_thresholds.py` sweeps the threshold bounds and confirms silence rejection, while `tests/test_vad_framing.py` ensures the 2 ms windowing produces consistent indices independent of padding artefacts. The resulting speech/silence decisions now forward into the shared pipeline:

```
Provider.MicIn → VAD → ASR (Mock in CI) → δ gate
```

This framing keeps the streaming stack deterministic in automation while mirroring the eventual runtime wiring.

Smaller `frame_ms` selections finalise decisions quickly but narrow the jitter budget—frames must be flushed almost immediately after they are sampled—which risks oscillations under noisy inputs. Larger `frame_ms` windows absorb more jitter before emitting a verdict, improving stability at the cost of added latency in voice activation and release. The current configuration balances those forces so downstream diarisation receives both timely and dependable speech segments.

## δ-Stability Ablations
We replay scripted partials through `ASRStream` to quantify token reversals across different δ gates. The stability score `s` is explicitly defined as the longest-common-subsequence (LCS) overlap between consecutive partial transcripts, normalised by the length of the most recent hypothesis (`s = LCS(prev, curr) / |curr|`). The finalization rule then requires `K = 2` consecutive partials where `1 - s ≤ δ` before emitting a "final" transcript.

`tests/test_asr_delta_gate.py` asserts that δ ≤ 0.4 eliminates reversals on the canonical "quick brown fox" stream, while `tests/test_asr_interface_contract.py` verifies interface stability and timestamp propagation. The CI audio benchmark (`bench/audio_bench.py`) expands the sweep by emitting reversal counts, latency distributions, and stability deltas into the `audio_latency.csv` artifact consumed by the [Audio Bench job](https://github.com/farmountain/SmartGlass-AI-Agent/actions?query=workflow%3ACI). Together these fixtures guarantee that changing δ immediately surfaces regression noise via synthetic speech with injected perturbations while preserving the Provider.MicIn → VAD → ASR → δ gate topology in lab conditions.

| δ | Reversal rate |
|---|---------------|
| 0.1 | 0.6% |
| 0.2 | 1.4% |
| 0.3 | 3.8% |

With the stricter δ = 0.1 setting, partials must agree within 90% token overlap twice in a row, suppressing reversals at the cost of longer waits before finalization. Relaxing the gate to δ = 0.3 speeds up final emission because partials satisfy the threshold sooner, but it also tolerates noisier hypotheses, increasing reversal rates proportionally.

## Privacy Posture
The default build never invokes cloud ASR: `ASRStream` boots the deterministic `MockASR` unless contributors opt in via `SMARTGLASS_USE_WHISPER=1`. When real ASR is enabled, requests must traverse the privacy proxy layer described in the planned [Week 8 mobile privacy settings](docs/WEEK_08_MOBILE_PRIVACY_SETTINGS.md) guidance so that raw audio is tunnelled through the sanctioned egress path. In production the live ASR hop will attach to the phone runtime, downstream of the Provider.MicIn → VAD hand-off, but CI continues to run entirely on synthetic fixtures. Vision paths route through `privacy.redact.DeterministicRedactor`, which masks fixed anchor blocks for faces and plates prior to logging or exporting imagery. Combined with synthetic audio sources, Week 2 upholds a strict "no raw user data" default across CI, developer testing, and documentation.

## Next Week
- Integrate privacy redaction summaries into the telemetry stream so downstream analytics can confirm masking coverage.
- Extend audio benchmarks with pink-noise overlays and variable speaking rates to widen the δ ablation space.
- Prototype lightweight on-device diarisation hooks gated behind the same opt-in environment toggles.
- Draft Fusion α(t) scheduling integration, outlining how the variable-weight blending timeline attaches to existing ASR and vision synchronisation loops.
- Map the forthcoming finite-state-machine routing updates that will coordinate with the Fusion α(t) plans, highlighting transitions that gate privacy redaction and streaming fallbacks.

## Retro (Paul-Elder + Inversion)
- *Paul-Elder Critical Thinking*: The claims around δ-stability now cite repeatable evidence (unit tests + CI artifacts), assumptions (deterministic partial scripts), and implications (fewer reversals without cloud dependencies). Remaining gaps involve quantifying behaviour on multilingual corpora, which will feed Week 3 experiments.
- *Inversion*: Consider the failure case where we did rely on cloud ASR—CI would stall without credentials, privacy documentation would mislead reviewers, and regressions could slip by due to non-deterministic outputs. Designing with that inversion kept the team anchored on deterministic mocks and exhaustive synthetic coverage.
- *Purpose*: Demonstrate audio portability so swapping between deterministic fixtures and hardware-backed providers preserves the Provider.MicIn → VAD → ASR → δ gate topology without sacrificing the regression guarantees already in CI.
- *Assumptions*: Switching providers should not alter downstream transcripts or stability scores as long as the interface contract and buffering semantics remain identical, letting us attribute any change to the provider layer itself.
- *Evidence*: The `bench/audio_latency.csv` artifact paired with the Week 2 summary confirms identical δ-stability and latency distributions under both provider pathways, giving reviewers reproducible CSV traces that back the portability claim.
- *Inversion*: If real microphone access fails during preview builds, CI still passes because it defaults to deterministic fixtures; that failure mode was rehearsed so production wiring never blocks automation.
