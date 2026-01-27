# Experience Encoder & Context Store Interfaces

This document defines interface-level contracts for an **Experience Encoder** (turning raw multimodal signals into structured “experience frames”) and a **Context Store** (persisting and retrieving those frames for downstream reasoning). It is intended to align with the existing `SmartGlassAgent`/`src/agent/` conventions and to provide implementers with stable typed structures, example payloads, and latency expectations.

## Scope & Intent

- **Experience Encoder**: Normalizes audio, vision, and text into a consistent schema that the agent and memory systems can consume.
- **Context Store**: Persists experience frames, action outputs, and skill metadata; provides retrieval primitives for prompt construction and task planning.
- **Alignment**: The schemas below mirror the `SmartGlassAgent.process_multimodal_query()` output fields (`response`, `actions`, `raw`) and existing action/skill conventions in `src/smartglass_agent.py`.

## Proposed Module Locations

Implementers can place these interfaces in the following modules (Python first, with optional Rust bindings for on-device runtime):

- `src/experience_encoder.py` — main encoder interface + schema definitions
- `src/context_store.py` — storage interface (in-memory, sqlite, vector DB, or remote)
- `src/agent/` — agent orchestration calls into encoder + store
- Optional Rust bindings (if needed for edge performance):
  - `src/rust/experience_encoder.rs` or `crates/experience_encoder/src/lib.rs`
  - FFI surface in `src/ffi/experience_encoder.py` (or `sdk_python/`)

## Interface Overview

### Experience Encoder

```text
Raw Inputs (audio/image/text + metadata)
  -> ExperienceEncoder.encode(...)
  -> ExperienceFrame + Model Prompts
```

### Context Store

```text
ExperienceFrame + AgentOutput + SkillSignals
  -> ContextStore.write(...)
  -> ContextStore.query(...)
  -> ContextStore.session_state(...)
```

## Typed Structures (Python-style)

> These are **reference schemas**; implementers may use `dataclasses`, `pydantic`, or `TypedDict` so long as field names/types are preserved.

```python
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class ExperienceInput:
    session_id: str
    timestamp_ms: int
    audio_input: Optional[str] = None  # file path or base64 url
    image_input: Optional[str] = None  # file path or base64 url
    text_query: Optional[str] = None
    language: Optional[str] = None
    cloud_offload: bool = False
    sensor_metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class VisualContext:
    description: str
    embeddings: Optional[List[float]] = None
    redaction_summary: Optional[Dict[str, Any]] = None

@dataclass
class ExperienceFrame:
    frame_id: str
    session_id: str
    timestamp_ms: int
    query: str
    visual_context: VisualContext
    metadata: Dict[str, Any]
    # Mirrors SmartGlassAgent action conventions
    actions: List[Dict[str, Any]] = field(default_factory=list)
    # Raw payload mirrors SmartGlassAgent.raw
    raw: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AgentOutput:
    response: str
    actions: List[Dict[str, Any]]
    raw: Dict[str, Any]
    redaction: Optional[Dict[str, Any]] = None

@dataclass
class ContextQuery:
    session_id: str
    query: str
    k: int = 8
    time_range_ms: Optional[List[int]] = None
    include_actions: bool = True
    include_raw: bool = False

@dataclass
class ContextResult:
    session_id: str
    frames: List[ExperienceFrame]
    summary: Optional[str] = None
```

### Action Shape (Normalized)

Aligned to `SmartGlassAgent._build_action()` and `process_multimodal_query()`:

```json
{
  "type": "skill_invocation",
  "skill_id": "skill_021",
  "payload": {
    "destination": "Cafe",
    "mode": "walk"
  },
  "source": "llm_json",
  "result": null
}
```

## JSON Schema (Representative)

### ExperienceEncoder.encode() Input

```json
{
  "session_id": "session_9b3a",
  "timestamp_ms": 1732134212345,
  "audio_input": "s3://bucket/audio.wav",
  "image_input": "s3://bucket/frame.jpg",
  "text_query": null,
  "language": "en",
  "cloud_offload": true,
  "sensor_metadata": {
    "gps": {"lat": 37.7749, "lon": -122.4194},
    "device": "meta_rayban_gen2",
    "battery_pct": 0.62
  }
}
```

### ExperienceEncoder.encode() Output

```json
{
  "frame_id": "frame_000123",
  "session_id": "session_9b3a",
  "timestamp_ms": 1732134212345,
  "query": "Find the nearest coffee shop.",
  "visual_context": {
    "description": "A city street with storefronts and pedestrians.",
    "embeddings": [0.02, -0.11, 0.08],
    "redaction_summary": {
      "faces_masked": 1,
      "plates_masked": 0
    }
  },
  "metadata": {
    "cloud_offload": true,
    "redaction_summary": {
      "faces_masked": 1,
      "plates_masked": 0
    }
  },
  "actions": [
    {
      "type": "skill_invocation",
      "skill_id": "skill_021",
      "payload": {"destination": "Cafe", "mode": "walk"},
      "source": "llm_json"
    }
  ],
  "raw": {
    "query": "Find the nearest coffee shop.",
    "visual_context": "A city street with storefronts and pedestrians.",
    "metadata": {
      "cloud_offload": true,
      "redaction_summary": {"faces_masked": 1, "plates_masked": 0}
    },
    "skills": [{"id": "skill_021", "name": "Wayfinding"}]
  }
}
```

### ContextStore.query() Output (example)

```json
{
  "session_id": "session_9b3a",
  "frames": [
    {
      "frame_id": "frame_000122",
      "session_id": "session_9b3a",
      "timestamp_ms": 1732134201000,
      "query": "What's that building?",
      "visual_context": {
        "description": "A tall glass building with a blue logo.",
        "embeddings": [0.03, -0.02, 0.15]
      },
      "metadata": {"cloud_offload": false},
      "actions": [],
      "raw": {
        "query": "What's that building?",
        "visual_context": "A tall glass building with a blue logo.",
        "metadata": {"cloud_offload": false}
      }
    }
  ],
  "summary": "User is walking downtown asking about nearby places."
}
```

## Expected Latency Targets

These are **interface-level expectations** for implementation planning. Actual SLAs may vary by hardware and model size.

| Stage | Target p50 | Target p95 | Notes |
| --- | --- | --- | --- |
| Audio transcription (Whisper) | ≤ 450 ms | ≤ 900 ms | For short (<5s) audio clips on GPU or optimized edge runtime. |
| Vision captioning (CLIP/vision) | ≤ 250 ms | ≤ 600 ms | Assumes local inference and pre-warmed model. |
| LLM response generation | ≤ 800 ms | ≤ 1500 ms | For short prompts and small/medium models. |
| ExperienceEncoder.encode() total | ≤ 1200 ms | ≤ 2300 ms | Includes audio + vision + LLM. |
| ContextStore.write() | ≤ 40 ms | ≤ 80 ms | Local db/vector store target. |
| ContextStore.query() | ≤ 120 ms | ≤ 250 ms | Includes embedding lookup and optional summary. |

## Integration Notes for `SmartGlassAgent` and `src/agent/`

- **Input parity**: The encoder input mirrors `SmartGlassAgent.process_multimodal_query()` arguments (`audio_input`, `image_input`, `text_query`, `language`, `cloud_offload`).
- **Output parity**: `ExperienceFrame.actions` and `raw` should reuse the action shapes built by `SmartGlassAgent._build_action()` and the raw payload in `process_multimodal_query()`.
- **Skill signals**: When `skill_signals` are available from RaySkillKit or other runtime adapters, they should be merged into `actions` and into `raw["skills"]` to keep agent behavior consistent.
- **Session binding**: `session_id` is required so that `ContextStore` can feed conversation context back into the agent loop.

## Suggested Interface Methods (Signatures)

```python
class ExperienceEncoder:
    def encode(self, payload: ExperienceInput) -> ExperienceFrame:
        """Transforms raw multimodal inputs into a normalized ExperienceFrame."""

class ContextStore:
    def write(self, frame: ExperienceFrame, output: AgentOutput) -> None:
        """Persist a frame + output for retrieval and audit trails."""

    def query(self, query: ContextQuery) -> ContextResult:
        """Retrieve recent or semantically similar frames for a session."""

    def session_state(self, session_id: str) -> Dict[str, Any]:
        """Return aggregated session context (last action, preferences, etc.)."""
```

## Implementation Checklist

- [ ] Define `ExperienceInput`, `ExperienceFrame`, `AgentOutput` in `src/experience_encoder.py`.
- [ ] Implement `ExperienceEncoder.encode()` wrapper around `SmartGlassAgent.process_multimodal_query()`.
- [ ] Define `ContextStore` interface in `src/context_store.py` with storage adapters.
- [ ] Ensure action payloads conform to the `SmartGlassAgent` action schema.
- [ ] Add tests for schema consistency and latency instrumentation hooks.
