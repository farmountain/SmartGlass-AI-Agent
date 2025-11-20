# SmartGlass AI Agent Whitepaper

## Executive Summary
- **Edge-native latency** – The Week 4 hero benchmark keeps end-to-end latency below 91 ms p95 even with captioning and TTS enabled, leaving >4 ms of slack versus the 95 ms SLA budget and sustaining two-digit requests per second (RPS) from a single worker.
- **Token-thrift architecture** – δ-gated ASR streaming plus fusion gates treat partial hypotheses as first-class signals, suppressing 84% of reversal-induced retransmits compared with a permissive gate, which slashes duplicated tokens before they reach LLM back ends.
- **Operational assurance** – Deterministic privacy redaction, red-team templates for safety and health scenarios, and explicit "信息辅助 only; ask/deny at high σ" guardrails for care-adjacent experiences anchor rollout reviews and demo scripts.

## Quantitative Token-Thrift Math

### Latency Envelope
The latest CI artifact (`docs/artifacts/week_04_e2e_hero1.csv`) decomposes every major stage. The observed p95 total of **90.67 ms** is driven primarily by captioning (48.49 ms) and keyframe extraction (34.98 ms), while other stages each contribute <5 ms.

| Stage | Target p95 (ms) | Observed p50 (ms) | Observed p95 (ms) | Target Margin |
| --- | --- | --- | --- | --- |
| synth_clip | 5 | 0.339 | 1.790 | +3.210 |
| synth_audio | 5 | 0.228 | 0.936 | +4.064 |
| vad | 6 | 3.529 | 4.510 | +1.490 |
| asr | 5 | 0.120 | 0.438 | +4.562 |
| keyframe | 40 | 31.755 | 34.980 | +5.020 |
| fusion_audio | 1 | 0.007 | 0.009 | +0.991 |
| fusion_vision | 1 | 0.001 | 0.001 | +0.999 |
| fusion_gate | 1 | 0.026 | 0.037 | +0.963 |
| fsm | 2 | 0.005 | 0.009 | +1.991 |
| caption | 55 | 43.512 | 48.493 | +6.507 |
| tts | 8 | 1.249 | 1.534 | +6.466 |
| total | 95 | 80.910 | 90.670 | +4.330 |

### Throughput Envelope
With a 90.67 ms p95 total, a single worker can sustain **≈11.0 RPS** (1 / 0.09067 s). Horizontal scaling is linear because stages are decoupled via queues, so doubling workers doubles throughput while preserving the latency profile until captioning saturates the GPU pool.

### Token-Thrift Efficiency
Week 2 δ-gating experiments show that tightening the gate from δ = 0.3 (3.8% reversal rate) to δ = 0.1 (0.6%) eliminates **3.2%** of duplicated partials. Because each reversal typically retransmits a full hypothesis, eliminating those reversals saves roughly 0.032 × `T` tokens per `T`-token session. For a 1 M token day, that is **32,000 tokens** protected from replay—an 84% reduction in reversal overhead (1 - 0.006 / 0.038).

### Cost Impact
Let `p` denote the per-million-token contract rate. Each million-token tranche now spends `(1 - 0.032) × p` instead of `p`, trimming the bill by **3.2% × p** (e.g., at $0.50 / 1M tokens, the delta is $0.016). When combined with the 11 RPS ceiling, the platform can process **950k tokens per day** at steady state (11 RPS × 75 tokens/req × 3600 × 2 h runtime windows for care teams) while holding the budget line.

## KPI Rollup from Latest Benchmarks
- **Latency SLA adherence:** 100% of stages stayed inside their targets with ≥0.96 ms of headroom, protecting the 95 ms end-to-end limit.
- **Caption dominance:** Captioning represents 53% of the total budget; trimming 10 ms there unlocks 11% more throughput without any other tuning.
- **Fusion determinism:** Combined fusion latency (audio + vision + gate + FSM) is <1 ms p95, confirming that synchronization logic will not gate larger workload bursts.

## Demo Video Outlines
1. **"Patient Whisper" (On-device bedside scribe)**
   - Hook: clinician dons SmartGlass to receive bilingual captions and summaries.
   - Beats: mic activation → δ-gated ASR transcript → live caption overlay → privacy-preserving export.
   - Proof: Show caption p95 <50 ms and deterministic redaction summary per encounter.

2. **"Warehouse Assist" (Hands-free order picking)**
   - Hook: worker scans shelves; keyframe detector guides them with audio prompts.
   - Beats: keyframe capture → fusion gate selection → FSM route into instructions → low-latency TTS playback.
   - Proof: Display KPI overlay showing 34.98 ms p95 keyframe stage and <2 ms TTS start.

3. **"Field Triage" (Safety-forward responder flow)**
   - Hook: responder queries for safe medical guidance.
   - Beats: VAD-triggered ASR → health skill template enforcing "信息辅助 only; ask/deny at high σ" responses → audit log citing red-team scenarios.
   - Proof: Pause to show decision tree referencing redteam health prompts and the denial fallback on self-harm or cardiac emergencies.

## Security & Privacy One-Pager
- **Deterministic redaction:** Every captured frame traverses `privacy.redact.DeterministicRedactor`, masking anchored facial and license-plate regions before storage, and emitting `RedactionSummary` counters for telemetry review.
- **Streaming discipline:** Audio remains on-device by default; `ASRStream` only escalates to remote ASR behind opt-in env vars, ensuring that CI and most demos never emit raw speech off the headset.
- **Red-team coverage:** Safety (`redteam/safety_scenarios.yaml`) and health (`redteam/health.yaml`) suites rehearse baseline greetings, frustration vents, exploitation attempts, and medical emergencies, supplying scripted expected decisions so demo crews can dry-run escalations.
- **Health skill guardrails:** Responses in regulated care contexts follow the **"信息辅助 only; ask/deny at high σ"** rule—provide informational assistance, escalate or deny when uncertainty spikes, and never render diagnoses. This note belongs in every scenario runbook and is reinforced by the red-team prompts covering self-harm and cardiac emergencies.
- **Privacy attestation:** Benchmarks and demos log the active privacy posture (redaction enabled, cloud ASR disabled, fusion queues cleared) so auditors can match KPI snapshots to their guardrail configuration.

