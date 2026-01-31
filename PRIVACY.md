# Edge runtime privacy defaults

The edge runtime is designed to avoid retaining personal data by default. All storage of raw media is **opt-in** and controlled
through environment variables. Enable these settings only when you have explicit consent and a plan for handling sensitive
artifacts.

## Storage toggles

- `STORE_RAW_AUDIO` (default: `false`): Keep in-memory audio buffers and duration metadata after ingestion. Useful for
  debugging wake-word or VAD behavior; disable in production to avoid lingering microphone captures.
- `STORE_RAW_FRAMES` (default: `false`): Maintain recent video frames for reuse by downstream queries. When disabled, frames are
  processed and discarded immediately.
- `STORE_TRANSCRIPTS` (default: `false`): Preserve transcripts generated from audio ingestion and text queries. Leave disabled to
  minimize exposure of user speech content.

When all flags remain at their defaults, session state only tracks lightweight metrics and query outputs—raw audio, images, and
transcripts are not persisted. Turning a flag on allows the associated buffers to be stored in memory but does not write them to
disk; you are responsible for clearing state when it is no longer needed.

---

# GDPR Compliance Checklist (Operational)

Use this section to document GDPR readiness for deployments that process EU resident data.

## Data Categories & Sources

| Category | Examples | Source | Default Retention |
| --- | --- | --- | --- |
| Audio | Voice commands, ambient speech | Glasses microphone | Not stored (in-memory only if `STORE_RAW_AUDIO=true`) |
| Images | Camera frames, photos | Glasses camera | Not stored (in-memory only if `STORE_RAW_FRAMES=true`) |
| Transcripts | Speech-to-text output | Whisper processing | Not stored (in-memory only if `STORE_TRANSCRIPTS=true`) |
| Action metadata | Skill IDs, actions executed | Agent output | Stored in session state for metrics only |
| Metrics | Latency, error counts | Edge runtime | Stored in aggregated metrics (no PII) |

## Legal Basis (Select one)

- **Consent** (recommended for consumer deployments)
- **Contract** (enterprise deployments with employee opt-in)
- **Legitimate Interests** (requires balancing test)

## Data Minimization Controls

- Raw media retention defaults to **off** (`false`).
- Redaction applied before any cloud offload (`cloud_offload=true`).
- Avoid storing full transcripts unless explicit consent is recorded.
- Use `metadata` fields to store only non-identifying operational data.

## User Rights Support

- **Access**: Provide a way to export session data on request.
- **Deletion**: Provide a way to delete session data (in-memory buffers and stored logs).
- **Correction**: Allow users to correct preferences and metadata.
- **Portability**: Export structured data (JSON) for user requests.

## Retention Policy

- Raw audio/frames/transcripts: **0 days by default** (in-memory only when enabled).
- Session metadata: **14–30 days** (configurable for analytics).
- Error logs: **7–14 days** (avoid PII).

## Security Measures

- TLS enforced for any network transport (HTTPS, WSS).
- API key or auth token required for edge runtime endpoints.
- Redaction pipeline applied before any cloud offload.
- Access controls for logs and metrics endpoints.

## DPIA (Data Protection Impact Assessment) Triggers

Perform a DPIA if any of the following are true:

- Processing biometric data or facial recognition outputs.
- Monitoring individuals in public spaces.
- Large-scale processing of audio or video.
- Any use in healthcare, education, or workplace surveillance.

## Incident Response

If a privacy incident occurs:

1. Identify impacted data types and scope.
2. Contain and stop data processing immediately.
3. Notify stakeholders within 72 hours if EU data is involved.
4. Document root cause and remediation.

## Deployment Checklist (GDPR)

- [ ] Consent flow implemented and recorded.
- [ ] Privacy policy provided to users.
- [ ] Data retention configured and documented.
- [ ] Data deletion process tested.
- [ ] Access logs reviewed (no PII).
- [ ] Redaction enabled for cloud offload.
- [ ] DPIA completed (if required).
