"""Configuration helpers for the edge runtime server."""

import json
import os
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class EdgeRuntimeConfig:
    """Runtime configuration for the edge API server."""

    provider: str
    whisper_model: str
    vision_model: str
    llm_backend_type: str
    ports: Dict[str, int] = field(default_factory=dict)
    api_key: str | None = None
    auth_token: str | None = None
    auth_header_name: str = "X-API-Key"
    audio_buffer_max_seconds: Optional[float] = None
    audio_buffer_max_bytes: Optional[int] = None
    frame_history_size: int = 1
    frame_buffer_max_bytes: Optional[int] = None


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
    api_key = os.getenv("EDGE_RUNTIME_API_KEY")
    auth_token = os.getenv("EDGE_RUNTIME_AUTH_TOKEN") or api_key
    auth_header_name = os.getenv("EDGE_RUNTIME_AUTH_HEADER", "X-API-Key")
    audio_buffer_max_seconds = _parse_optional_float(os.getenv("AUDIO_BUFFER_MAX_SECONDS"))
    audio_buffer_max_bytes = _parse_optional_int(os.getenv("AUDIO_BUFFER_MAX_BYTES"))
    frame_history_size = _parse_optional_int(os.getenv("FRAME_HISTORY_SIZE"), default=1) or 1
    frame_buffer_max_bytes = _parse_optional_int(os.getenv("FRAME_BUFFER_MAX_BYTES"))

    ports = _parse_ports_env(ports_env)

    return EdgeRuntimeConfig(
        provider=provider,
        whisper_model=whisper_model,
        vision_model=vision_model,
        llm_backend_type=llm_backend_type,
        ports=ports,
        api_key=api_key,
        auth_token=auth_token,
        auth_header_name=auth_header_name,
        audio_buffer_max_seconds=audio_buffer_max_seconds,
        audio_buffer_max_bytes=audio_buffer_max_bytes,
        frame_history_size=frame_history_size,
        frame_buffer_max_bytes=frame_buffer_max_bytes,
    )


def _parse_optional_int(raw_value: str | None, *, default: Optional[int] = None) -> Optional[int]:
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"Invalid integer value: {raw_value}") from exc


def _parse_optional_float(raw_value: str | None) -> Optional[float]:
    if raw_value is None:
        return None
    try:
        return float(raw_value)
    except ValueError as exc:
        raise ValueError(f"Invalid float value: {raw_value}") from exc
