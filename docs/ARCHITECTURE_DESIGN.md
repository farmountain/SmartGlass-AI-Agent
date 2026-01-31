# SmartGlass AI Agent — Architecture Design (v1.1)

**Goal**: Formalize core system layers, boundaries, and interfaces for long‑term maintainability and product evolution.

---

## 1. System Layers (AIVX-aligned)

| Layer | Responsibility | Module(s) |
| --- | --- | --- |
| Perception (Audio) | Speech capture + transcription | src/whisper_processor.py |
| Perception (Vision) | Scene understanding | src/clip_vision.py |
| Sensor I/O | Device adapters | drivers/providers/ |
| Fusion | Multimodal prompt & context | src/agent/ + SmartGlassAgent |
| **World Model** | State representation & scene context | src/world_model.py (new) |
| **Memory** | Experience storage & retrieval | src/context_store.py (new) |
| **Planning** | Task decomposition & action sequencing | src/planner.py (new) |
| Safety & Guardrails | Policy checks & moderation | src/safety/ |
| Telemetry | Metrics & observability | src/utils/metrics.py + planned telemetry interface |

---

## 2. Core Architectural Invariants

1. **Perception is Stateless**: Audio/vision processors must not retain user data beyond request scope.
2. **Policy Before Action**: Actions are validated by SafetyGuard before dispatch.
3. **Memory is Opt‑In**: Context storage is disabled by default; must be explicitly enabled.
4. **World Model is Interpretable**: State should be stored in typed objects (not raw strings).
5. **Planning is Deterministic**: Given identical inputs, planning output must be consistent.

---

## 3. Reference Flow

```
Input (Audio/Image/Text)
  -> Perception
  -> Fusion (prompt + context)
  -> Planner (task decomposition)
  -> LLM Backend
  -> Safety Guard
  -> Action Dispatcher
  -> Telemetry + Memory write (if enabled)
```

---

## 4. Minimal Interfaces (Contracts)

### World Model
- **Goal**: Represent real‑time context as structured state.
- **Key Objects**: `WorldState`, `SceneObject`, `UserIntent`.

### Context Store
- **Goal**: Persist experience frames for retrieval.
- **API**: `write(frame)`, `query(query)`, `session_state(session_id)`.

### Planner
- **Goal**: Turn high‑level intent into action sequences.
- **API**: `plan(intent, world_state, constraints)`.

---

## 5. Non‑Functional Targets

- **Latency**: p95 < 1.5s end‑to‑end
- **Safety**: 0 critical unsafe actions per 1,000 sessions
- **Memory**: < 200MB resident under load
- **Battery**: < 15%/hour drain on phone during continuous use

---

## 6. Next Implementation Steps

1. Add minimal interface classes for World Model, Context Store, Planner.
2. Wire SmartGlassAgent to use them when enabled.
3. Introduce telemetry interface for structured event logging.
4. Add integration tests for deterministic planning outputs.

---

**Status**: Architecture foundation defined. Interfaces stubbed in code for incremental implementation.
