#!/usr/bin/env python3
"""Render documentation KPI CSVs as Markdown tables.

The script locates the newest CSV file(s) under the provided artifacts
folder (default: ``docs/artifacts``), extracts the KPI columns, and
prints a Markdown table for each discovered file. If multiple CSVs share
the same newest timestamp, a table is printed for each of them in
alphabetical order.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Iterable, List

REQUIRED_COLUMNS = ("stage", "target_p95_ms", "observed_p50_ms", "observed_p95_ms")


def _format_number(value: str) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)

    if number.is_integer():
        return str(int(number))
    return f"{number:.3f}"


def _load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [column for column in REQUIRED_COLUMNS if column not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"Missing required columns in {path}: {', '.join(missing)}")
        return [row for row in reader if any((row.get(column) or "").strip() for column in REQUIRED_COLUMNS)]


def _render_table(rows: Iterable[dict[str, str]]) -> str:
    lines: List[str] = []
    header = ["Stage", "Target p95 (ms)", "Observed p50 (ms)", "Observed p95 (ms)"]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join("---" for _ in header) + " |")
    for row in rows:
        stage = (row.get("stage") or "").replace("_", " ").strip()
        target = _format_number(row.get("target_p95_ms") or "")
        observed_p50 = _format_number(row.get("observed_p50_ms") or "")
        observed_p95 = _format_number(row.get("observed_p95_ms") or "")
        lines.append(f"| {stage or 'n/a'} | {target} | {observed_p50} | {observed_p95} |")
    return "\n".join(lines)


def _find_newest_csvs(root: Path) -> list[Path]:
    candidates = []
    for path in root.rglob("*.csv"):
        if path.is_file():
            candidates.append((path, path.stat().st_mtime))

    if not candidates:
        return []

    newest_mtime = max(mtime for _, mtime in candidates)
    newest_paths = [path for path, mtime in candidates if mtime == newest_mtime]
    return sorted(newest_paths)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifacts",
        type=Path,
        default=Path("docs/artifacts"),
        help="Directory that contains KPI CSV artifacts (default: docs/artifacts)",
    )
    args = parser.parse_args(argv)

    if not args.artifacts.exists():
        print(f"_Artifacts directory not found: {args.artifacts}_", file=sys.stderr)
        return 0

    newest_paths = _find_newest_csvs(args.artifacts)
    if not newest_paths:
        print(f"_No KPI CSV files found under {args.artifacts}_", file=sys.stderr)
        return 0

    outputs: list[str] = []
    for path in newest_paths:
        rows = _load_rows(path)
        if not rows:
            table = "_KPI CSV was empty._"
        else:
            table = _render_table(rows)
        outputs.append(f"### {path.relative_to(args.artifacts)}\n\n{table}")

    print("\n\n".join(outputs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
