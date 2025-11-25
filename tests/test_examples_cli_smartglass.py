from __future__ import annotations

import builtins
import sys
from types import ModuleType


def _install_stub_modules() -> None:
    dummy_gpt2 = ModuleType("gpt2_generator")
    dummy_gpt2.GPT2Backend = type("DummyGPT2Backend", (), {})
    sys.modules.setdefault("gpt2_generator", dummy_gpt2)

    dummy_snn = ModuleType("llm_snn_backend")
    dummy_snn.SNNLLMBackend = type("DummySNNBackend", (), {})
    sys.modules.setdefault("llm_snn_backend", dummy_snn)

    dummy_agent_module = ModuleType("smartglass_agent")
    dummy_agent_module.SmartGlassAgent = type("StubAgent", (), {})
    sys.modules.setdefault("smartglass_agent", dummy_agent_module)


class _DummyAgent:
    def __init__(self, calls: list[str]):
        self.calls = calls
        self.calls.append("initialized")

    def process_multimodal_query(self, text_query: str, image_input: str | None = None):
        self.calls.append((text_query, image_input))
        return {"response": "stub response", "actions": [{"type": "mock-action"}]}


def test_cli_main_runs_with_mock(monkeypatch, capsys):
    _install_stub_modules()

    import examples.cli_smartglass as cli_smartglass

    calls: list[str] = []

    monkeypatch.setenv("PROVIDER", "mock")
    monkeypatch.setattr(cli_smartglass, "initialize_agent", lambda backend: _DummyAgent(calls))
    monkeypatch.setattr(cli_smartglass.sys, "argv", ["cli_smartglass"])

    user_inputs = iter(["hello", ""])  # exit on second prompt
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(user_inputs))

    cli_smartglass.main()
    captured = capsys.readouterr()

    assert "stub response" in captured.out
    assert "mock-action" in captured.out
    assert calls == ["initialized", ("hello", None)]
