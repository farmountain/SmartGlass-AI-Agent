"""Helpers for privacy-related storage flags.

These helpers centralize how environment variables for storing sensitive data
are parsed, ensuring defaults remain aligned with the privacy documentation.
"""

import os


def _parse_bool(raw_value: str | None, *, default: bool = False) -> bool:
    if raw_value is None:
        return default

    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(
        "Invalid boolean value; use one of: true, false, 1, 0, yes, no, on, off"
    )


def should_store_audio() -> bool:
    """Return whether raw audio buffers should be retained."""

    return _parse_bool(os.getenv("STORE_RAW_AUDIO"), default=False)


def should_store_frames() -> bool:
    """Return whether raw video frames should be retained."""

    return _parse_bool(os.getenv("STORE_RAW_FRAMES"), default=False)


def should_store_transcripts() -> bool:
    """Return whether transcripts should be retained."""

    return _parse_bool(os.getenv("STORE_TRANSCRIPTS"), default=False)

