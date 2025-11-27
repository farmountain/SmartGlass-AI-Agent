import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "action_builder", Path(__file__).resolve().parents[1] / "src" / "utils" / "action_builder.py"
)
if not spec or not spec.loader:  # pragma: no cover - defensive guard
    raise ImportError("Could not load action_builder module")
action_builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(action_builder)
ActionBuilder = action_builder.ActionBuilder


def test_capability_mapping_uses_skill_catalog():
    builder = ActionBuilder()

    assert builder.capability_to_skill["navigation"] == "skill_001"
    assert builder.capability_to_skill["vision"] == "skill_002"
    assert builder.capability_to_skill["speech"] == "skill_003"

    # Aliases fall back to the catalog-derived mapping
    assert builder.capability_to_skill["navigate"] == "skill_001"
    assert builder.capability_to_skill["read_sign"] == "skill_002"
    assert builder.capability_to_skill["transcribe"] == "skill_003"


def test_suggest_actions_validates_and_scaffolds_payloads():
    builder = ActionBuilder()

    actions = builder.suggest_actions(
        capabilities=["navigate", "read_sign"], skills=["skill_003", "skill_999"]
    )

    assert {action["skill_id"] for action in actions} == {
        "skill_001",
        "skill_002",
        "skill_003",
    }

    nav_action = next(action for action in actions if action["skill_id"] == "skill_001")
    assert nav_action["payload"]["mode"] == "navigate"
    assert nav_action["payload"]["capability_hint"] == "navigate"

    read_action = next(action for action in actions if action["skill_id"] == "skill_002")
    assert read_action["payload"]["query"] == "read_signage"

    transcribe_action = next(action for action in actions if action["skill_id"] == "skill_003")
    assert "audio" in transcribe_action["payload"]
    assert "language" in transcribe_action["payload"]
