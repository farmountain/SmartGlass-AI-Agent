# Action schema and RaySkillKit skill mapping

SmartGlass agent replies follow the [agent_output schema](../schemas/agent_output.schema.json) and emit normalized **actions** alongside the human-facing `response`. Each action is a dictionary with the following shape:

- `type` (**required**): semantic label for the invocation (for example `skill_invocation`, `navigate`, or `read_signage`).
- `skill_id` (optional): RaySkillKit identifier that should handle the request (validated against `rayskillkit/skills.json`).
- `payload` (optional): structured arguments to pass to the skill.
- `result` (optional): normalized output from the invoked skill or tool.
- `timestamp` / `source` (optional): execution time and origin (`llm_json`, `skill_runtime`, `text_match`, or `capability_hint`).

When the agent detects RaySkillKit usage, it also mirrors the full skill entries under `raw["skills"]` so clients can fetch metadata (name, description, capabilities, paths) before dispatching concrete calls.

## Sample action payloads

Typical RaySkillKit-backed actions follow a predictable payload layout derived from the bundled scaffold:

| Action type | Skill id | Purpose | Payload fields |
| --- | --- | --- | --- |
| `skill_invocation` | `skill_001` | Indoor navigation / routing | `{ "destination": "Gate C12", "waypoints": ["security"], "mode": "navigate" }` |
| `skill_invocation` | `skill_002` | Vision or sign reading | `{ "image": "images/scene.jpg", "query": "read_signage" }` |
| `skill_invocation` | `skill_003` | Speech → text | `{ "audio": "audio/command.wav", "language": "en" }` |

These payloads map directly onto the capability aliases defined in `src/utils/action_builder.py`, so callers can programmatically fill in filenames, buffers, or device handles before invoking RaySkillKit.

## Using actions and raw skills at runtime

```python
from src.smartglass_agent import SmartGlassAgent

agent = SmartGlassAgent()
result = agent.process_multimodal_query(text_query="Guide me to the coffee shop")

# Structured response
actions = result.get("actions", [])
skills = result.get("raw", {}).get("skills", [])

# Dispatch recognized RaySkillKit skills
for action in actions:
    if action.get("type") == "skill_invocation" and action.get("skill_id"):
        payload = action.get("payload", {})
        skill_id = action["skill_id"]
        print(f"Calling RaySkillKit skill {skill_id} with payload {payload}")
        # ray_skillkit.run(skill_id, **payload)

# Skill metadata can be inspected via raw["skills"]
for skill in skills:
    print(skill["id"], skill.get("capabilities"), skill.get("model_path"))
```

The `actions` list is ordered, so you can replay complex chains (for example, detect → translate → summarize). When `raw["skills"]` is present, it enumerates every RaySkillKit entry that the agent inferred from LLM output, JSON blocks, runtime signals, or capability hints, making it safe to bind to the correct binary or stats bundle before executing the workload.
