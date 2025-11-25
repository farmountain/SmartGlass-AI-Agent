"""Helpers for validating agent responses against published schemas.

This module centralizes access to the agent output schema so that test suites
and debug tooling can enforce that :py:meth:`SmartGlassAgent.process_multimodal_query`
returns payloads that conform to the documented response envelope.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import jsonschema

AGENT_OUTPUT_KEYS = ("response", "actions", "raw")


@lru_cache()
def _load_agent_output_schema() -> dict[str, Any]:
    """Load and cache the JSON schema for agent outputs."""

    schema_path = Path(__file__).resolve().parents[2] / "schemas" / "agent_output.schema.json"
    with schema_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def validate_agent_output_schema(agent_output: Mapping[str, Any], *, strip_additional_keys: bool = True) -> None:
    """Validate a ``process_multimodal_query`` result against the schema.

    Parameters
    ----------
    agent_output:
        The dictionary returned from ``process_multimodal_query``.
    strip_additional_keys:
        When ``True`` (default), only the canonical ``response``, ``actions``,
        and ``raw`` fields are validated to avoid false positives from extra
        helper fields. Set to ``False`` to validate the entire payload.

    Raises
    ------
    jsonschema.ValidationError
        If the envelope fails schema validation.
    ValueError
        If required envelope keys are missing when ``strip_additional_keys``
        is enabled.
    """

    if strip_additional_keys:
        missing_keys = [key for key in AGENT_OUTPUT_KEYS if key not in agent_output]
        if missing_keys:
            raise ValueError(f"Missing required keys for agent output validation: {', '.join(missing_keys)}")
        payload: Mapping[str, Any] = {key: agent_output[key] for key in AGENT_OUTPUT_KEYS}
    else:
        payload = agent_output

    schema = _load_agent_output_schema()
    validator = jsonschema.Draft202012Validator(schema)
    validator.validate(payload)
