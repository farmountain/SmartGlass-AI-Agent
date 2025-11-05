#!/usr/bin/env python3
"""Validate the RaySkillKit skills catalogue against its JSON Schema."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import jsonschema
except ModuleNotFoundError as exc:  # pragma: no cover - dependency failure
    raise SystemExit(
        "The 'jsonschema' package is required to validate skills data. "
        "Install it with 'pip install jsonschema'."
    ) from exc


def load_json(path: Path) -> dict:
    """Load JSON from *path* and return the parsed object."""

    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        location = f"line {exc.lineno}, column {exc.colno}"
        raise SystemExit(f"Invalid JSON in {path}: {exc.msg} ({location})") from exc


def validate(skills_path: Path, schema_path: Path) -> int:
    """Validate *skills_path* against *schema_path*.

    Returns 0 when the skills data conforms to the schema, otherwise 1.
    """

    schema = load_json(schema_path)
    skills = load_json(skills_path)

    try:
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(schema)
    except jsonschema.SchemaError as exc:
        raise SystemExit(f"Invalid schema definition: {exc.message}") from exc

    errors = sorted(validator.iter_errors(skills), key=lambda err: err.path)
    if not errors:
        return 0

    for error in errors:
        path = "/".join(str(part) for part in error.path) or "<root>"
        print(f"[ERROR] {path}: {error.message}", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skills",
        default=Path(__file__).resolve().parent.parent / "rayskillkit" / "skills.json",
        type=Path,
        help="Path to the skills.json file (defaults to repository copy).",
    )
    parser.add_argument(
        "--schema",
        default=Path(__file__).resolve().parent.parent
        / "rayskillkit"
        / "schemas"
        / "skills.schema.json",
        type=Path,
        help="Path to the skills schema JSON file (defaults to repository copy).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    return validate(args.skills, args.schema)


if __name__ == "__main__":
    sys.exit(main())
