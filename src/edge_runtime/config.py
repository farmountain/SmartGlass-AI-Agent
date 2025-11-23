"""Configuration helpers for the edge runtime server."""

import json
import os
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class EdgeRuntimeConfig:
    """Runtime configuration for the edge API server."""

    provider: str
    whisper_model: str
    vision_model: str
    llm_backend_type: str
    ports: Dict[str, int] = field(default_factory=dict)


def _parse_ports_env(ports_env: str | None) -> Dict[str, int]:
    """Parse the PORTS environment variable into a mapping.

    Supported formats:
    - JSON object: ``{"http": 8000, "metrics": 9000}``
    - Comma-separated list: ``http:8000,metrics:9000``
    - Single port: ``8000`` (mapped to ``{"http": 8000}``)
    """

    if not ports_env:
        return {"http": 8000}

    ports_env = ports_env.strip()
    if ports_env.isdigit():
        return {"http": int(ports_env)}

    if ports_env.startswith("{"):
        try:
            parsed = json.loads(ports_env)
            return {k: int(v) for k, v in parsed.items()}
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError("Invalid JSON provided in PORTS environment variable") from exc

    ports: Dict[str, int] = {}
    for entry in ports_env.split(","):
        if not entry:
            continue
        if ":" in entry:
            name, value = entry.split(":", 1)
        else:
            name, value = "http", entry
        try:
            ports[name.strip()] = int(value)
        except ValueError as exc:
            raise ValueError(f"Invalid port value for entry '{entry}'") from exc

    return ports or {"http": 8000}


def load_config_from_env() -> EdgeRuntimeConfig:
    """Load :class:`EdgeRuntimeConfig` from environment variables."""

    provider = os.getenv("PROVIDER", "local")
    whisper_model = os.getenv("WHISPER_MODEL", "base")
    vision_model = os.getenv("VISION_MODEL", "openai/clip-vit-base-patch32")
    llm_backend_type = os.getenv("LLM_BACKEND_TYPE", "ann")
    ports_env = os.getenv("PORTS")

    ports = _parse_ports_env(ports_env)

    return EdgeRuntimeConfig(
        provider=provider,
        whisper_model=whisper_model,
        vision_model=vision_model,
        llm_backend_type=llm_backend_type,
        ports=ports,
    )
