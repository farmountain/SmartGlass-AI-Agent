# AIVX Architecture Mapping

This document maps each AIVX layer to the current repository modules and entry points. Where a layer has no direct counterpart today, it is called out explicitly and marked as a planned module.

## Layer Mapping

| AIVX Layer | Current Modules / Entry Points | Notes |
| --- | --- | --- |
| **Perception (Audio/Speech)** | `src/whisper_processor.py` | Whisper-based speech/audio perception pipeline. |
| **Perception (Vision)** | `src/clip_vision.py` | Vision embedding/perception utilities. |
| **Sensor I/O / Drivers** | `drivers/providers/` | Hardware and sensor provider integrations. |
| **Policy / Action Formatting** | `src/agent/` | Agent policy logic, action formatting, and orchestration. |
| **World Model / State** | **Planned module** | No direct module found; intended home for state estimation and scene/world modeling. |
| **Memory (Short/Long-term)** | **Planned module** | No explicit memory subsystem located; to be introduced. |
| **Planning / Task Decomposition** | **Planned module** | No dedicated planner module present; planned addition. |
| **Safety / Guardrails** | **Planned module** | No explicit safety/guardrail layer identified. |
| **Learning / Adaptation** | **Planned module** | No on-line/off-line learning layer mapped yet. |
| **Evaluation / Telemetry** | **Planned module** | No central evaluation or telemetry layer mapped yet. |

## Notes

- The above mappings are based on current repository structure and explicit entry points that align to AIVX layers.
- Planned modules should be added as dedicated packages once their scope and ownership are defined.
