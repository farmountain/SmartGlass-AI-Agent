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
