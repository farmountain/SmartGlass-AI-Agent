#!/usr/bin/env python3
"""Repository inventory utility.

This script walks the repository, captures lightweight metadata about every file,
serialises a machine-readable inventory, and seeds the accompanying markdown
reports.  The goal is to provide a quick snapshot of the current codebase state
and highlight any risky findings (such as secrets committed to the repo or
legacy default GPT-2 usage).

The layout intentionally mirrors the "Week 1" automation exercises used in
SmartGlass bootcamps: generate an `artifacts` payload and refresh the
human-readable docs in `docs/`.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence, Tuple
import re
import sys

DEFAULT_IGNORE_DIRS = {".git", "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache", "artifacts"}
TEXT_EXTENSIONS = {
    ".py",
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".js",
    ".ts",
    ".tsx",
    ".css",
    ".html",
}
SECRET_PATTERNS: Sequence[Tuple[str, str]] = (
    (r"sk-[A-Za-z0-9]{32,}", "Potential OpenAI-style API key"),
    (r"AIza[0-9A-Za-z\-_]{35}", "Potential Google API key"),
    (r"AKIA[0-9A-Z]{16}", "Potential AWS access key"),
    (r"hf_[A-Za-z0-9]{30,}", "Potential HuggingFace token"),
)
GPT2_PATTERN = re.compile(r"([\"'])gpt-?2\1", re.IGNORECASE)

VENDOR_LOCKIN_PATTERNS: Sequence[Tuple[re.Pattern[str], str]] = (
    (re.compile(r"meta.*wearable", re.IGNORECASE | re.DOTALL), "Meta wearable vendor reference detected."),
    (re.compile(r"com\.vuzix", re.IGNORECASE), "Vuzix vendor package reference detected."),
    (re.compile(r"xreal", re.IGNORECASE), "XREAL vendor reference detected."),
    (re.compile(r"openxr", re.IGNORECASE), "OpenXR SDK reference detected."),
    (re.compile(r"arfoundation", re.IGNORECASE), "AR Foundation dependency reference detected."),
    (re.compile(r"visionos", re.IGNORECASE), "visionOS platform reference detected."),
    (re.compile(r"tesseract", re.IGNORECASE), "Tesseract OCR dependency reference detected."),
    (re.compile(r"easyocr", re.IGNORECASE), "EasyOCR dependency reference detected."),
)
SDK_IMPORT_PATTERN = re.compile(r"from\s+(sdk_[A-Za-z0-9_]+)\s+import", re.IGNORECASE)
VENDOR_LOCKIN_EXCLUDE_PATHS = {
    "docs/INVENTORY.md",
    "docs/TECH_DEBT.md",
    "scripts/inventory_repo.py",
}


@dataclasses.dataclass
class FileRecord:
    path: str
    size: int
    modified: str
    extension: str
    is_binary: bool

    def to_json(self) -> Dict[str, object]:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class FlaggedFinding:
    path: str
    description: str
    snippet: Optional[str] = None

    def to_json(self) -> Dict[str, object]:
        data = {"path": self.path, "description": self.description}
        if self.snippet:
            data["snippet"] = self.snippet
        return data


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a repository inventory and markdown reports.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root (defaults to current working directory).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with a non-zero status code if critical findings are detected.",
    )
    return parser.parse_args(argv)


def is_binary_file(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            chunk = handle.read(1024)
    except OSError:
        return True
    if b"\0" in chunk:
        return True
    try:
        chunk.decode("utf-8")
    except UnicodeDecodeError:
        return True
    return False


def iter_files(repo_root: Path) -> Iterator[Path]:
    for dirpath, dirnames, filenames in os.walk(repo_root):
        # In-place prune directories that should be ignored.
        dirnames[:] = [d for d in dirnames if d not in DEFAULT_IGNORE_DIRS and not d.startswith('.')]
        for filename in filenames:
            full_path = Path(dirpath, filename)
            if full_path.is_symlink():
                continue
            yield full_path


def collect_inventory(
    repo_root: Path,
) -> Tuple[
    List[FileRecord],
    Counter[str],
    List[FlaggedFinding],
    List[FlaggedFinding],
    List[FlaggedFinding],
]:
    records: List[FileRecord] = []
    by_extension: Counter[str] = Counter()
    secret_flags: List[FlaggedFinding] = []
    gpt2_flags: List[FlaggedFinding] = []
    vendor_lockin_flags: List[FlaggedFinding] = []
    vendor_lockin_seen: set[Tuple[str, str]] = set()

    for file_path in iter_files(repo_root):
        rel_path = file_path.relative_to(repo_root).as_posix()
        stat = file_path.stat()
        extension = file_path.suffix.lower()
        is_binary = is_binary_file(file_path)
        records.append(
            FileRecord(
                path=rel_path,
                size=stat.st_size,
                modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                extension=extension or "<none>",
                is_binary=is_binary,
            )
        )
        by_extension[extension or "<none>"] += 1

        def add_vendor_flag(description: str, snippet: Optional[str] = None) -> None:
            if rel_path in VENDOR_LOCKIN_EXCLUDE_PATHS:
                return
            key = (rel_path, description)
            if key not in vendor_lockin_seen:
                vendor_lockin_seen.add(key)
                vendor_lockin_flags.append(
                    FlaggedFinding(path=rel_path, description=description, snippet=snippet)
                )

        # Scan the path itself for vendor-specific tokens.
        if rel_path not in VENDOR_LOCKIN_EXCLUDE_PATHS:
            for pattern, description in VENDOR_LOCKIN_PATTERNS:
                if pattern.search(rel_path):
                    add_vendor_flag(description)

        if not is_binary or extension in TEXT_EXTENSIONS:
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for pattern, description in SECRET_PATTERNS:
                match = re.search(pattern, text)
                if match:
                    snippet_start = max(match.start() - 20, 0)
                    snippet_end = min(match.end() + 20, len(text))
                    snippet = text[snippet_start:snippet_end].replace("\n", " ")
                    secret_flags.append(
                        FlaggedFinding(path=rel_path, description=description, snippet=snippet)
                    )
            if GPT2_PATTERN.search(text):
                gpt2_flags.append(
                    FlaggedFinding(path=rel_path, description="Reference to GPT-2 detected.")
                )

            for pattern, description in VENDOR_LOCKIN_PATTERNS:
                for match in pattern.finditer(text):
                    snippet_start = max(match.start() - 20, 0)
                    snippet_end = min(match.end() + 20, len(text))
                    snippet = text[snippet_start:snippet_end].replace("\n", " ")
                    add_vendor_flag(description, snippet)

            for match in SDK_IMPORT_PATTERN.finditer(text):
                module_name = match.group(1)
                snippet_start = max(match.start() - 20, 0)
                snippet_end = min(match.end() + 20, len(text))
                snippet = text[snippet_start:snippet_end].replace("\n", " ")
                add_vendor_flag(f"Vendor SDK import `{module_name}` detected.", snippet)

    return records, by_extension, secret_flags, gpt2_flags, vendor_lockin_flags


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_inventory_json(
    output_path: Path,
    repo_root: Path,
    records: Sequence[FileRecord],
    by_extension: Counter[str],
    secret_flags: Sequence[FlaggedFinding],
    gpt2_flags: Sequence[FlaggedFinding],
    vendor_lockin_flags: Sequence[FlaggedFinding],
) -> None:
    ensure_directory(output_path.parent)
    payload = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "repo_root": str(repo_root),
        "file_count": len(records),
        "total_bytes": sum(record.size for record in records),
        "by_extension": dict(sorted(by_extension.items(), key=lambda item: item[0])),
        "flags": {
            "potential_secrets": [flag.to_json() for flag in secret_flags],
            "default_gpt2_references": [flag.to_json() for flag in gpt2_flags],
            "vendor_lock_in": [flag.to_json() for flag in vendor_lockin_flags],
        },
        "files": [record.to_json() for record in records],
    }
    output_path.write_text(json.dumps(payload, indent=2))


def format_size(num_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


def write_inventory_markdown(
    inventory_path: Path,
    repo_root: Path,
    records: Sequence[FileRecord],
    by_extension: Counter[str],
    secret_flags: Sequence[FlaggedFinding],
    gpt2_flags: Sequence[FlaggedFinding],
    vendor_lockin_flags: Sequence[FlaggedFinding],
) -> None:
    ensure_directory(inventory_path.parent)
    total_bytes = sum(record.size for record in records)
    lines: List[str] = []
    lines.append("# Repository Inventory")
    lines.append("")
    lines.append(f"- Generated: {datetime.now(tz=timezone.utc).isoformat()}")
    lines.append(f"- Repository root: `{repo_root}`")
    lines.append(f"- Files tracked: {len(records)}")
    lines.append(f"- Total size: {format_size(total_bytes)}")
    lines.append("")

    lines.append("## File Type Breakdown")
    lines.append("")
    lines.append("| Extension | Count |")
    lines.append("| --- | ---: |")
    for ext, count in sorted(by_extension.items(), key=lambda item: (-item[1], item[0])):
        label = ext if ext != "<none>" else "(no extension)"
        lines.append(f"| `{label}` | {count} |")
    lines.append("")

    if secret_flags or gpt2_flags or vendor_lockin_flags:
        lines.append("## Alerts")
        lines.append("")
        if secret_flags:
            lines.append("### Potential secrets")
            lines.append("")
            for flag in secret_flags:
                snippet = f" — `{flag.snippet}`" if flag.snippet else ""
                lines.append(f"- `{flag.path}`: {flag.description}{snippet}")
            lines.append("")
        if gpt2_flags:
            lines.append("### Default GPT-2 references")
            lines.append("")
            for flag in gpt2_flags:
                lines.append(f"- `{flag.path}`: {flag.description}")
            lines.append("")
        if vendor_lockin_flags:
            lines.append("### Vendor Lock-In")
            lines.append("")
            lines.append("| Path | Trigger |")
            lines.append("| --- | --- |")
            for flag in vendor_lockin_flags:
                lines.append(f"| `{flag.path}` | {flag.description} |")
            lines.append("")
            lines.append("#### Move behind DAL")
            lines.append("")
            for flag in vendor_lockin_flags:
                lines.append(f"- `{flag.path}` — {flag.description}")
            lines.append("")
    else:
        lines.append("## Alerts")
        lines.append("")
        lines.append("No critical findings detected.")
        lines.append("")

    largest = sorted(records, key=lambda record: record.size, reverse=True)[:10]
    lines.append("## Largest Files")
    lines.append("")
    lines.append("| Path | Size |")
    lines.append("| --- | ---: |")
    for record in largest:
        lines.append(f"| `{record.path}` | {format_size(record.size)} |")
    lines.append("")

    inventory_path.write_text("\n".join(lines))


def write_tech_debt_markdown(
    tech_debt_path: Path,
    secret_flags: Sequence[FlaggedFinding],
    gpt2_flags: Sequence[FlaggedFinding],
    vendor_lockin_flags: Sequence[FlaggedFinding],
) -> None:
    ensure_directory(tech_debt_path.parent)
    lines: List[str] = []
    lines.append("# Tech Debt & Risk Register")
    lines.append("")
    lines.append("This document is generated by `scripts/inventory_repo.py`.  It captures the latest")
    lines.append("alerts that may require engineering follow-up.")
    lines.append("")

    if not secret_flags and not gpt2_flags and not vendor_lockin_flags:
        lines.append("No tech debt findings detected during the last scan.")
    else:
        if secret_flags:
            lines.append("## Potential Secrets")
            lines.append("")
            for flag in secret_flags:
                snippet = f" — `{flag.snippet}`" if flag.snippet else ""
                lines.append(f"- `{flag.path}`: {flag.description}{snippet}")
            lines.append("")
        if gpt2_flags:
            lines.append("## Default GPT-2 Usage")
            lines.append("")
            for flag in gpt2_flags:
                lines.append(f"- `{flag.path}`: {flag.description}")
            lines.append("")
        if vendor_lockin_flags:
            lines.append("## Vendor Lock-In")
            lines.append("")
            lines.append("| Path | Trigger |")
            lines.append("| --- | --- |")
            for flag in vendor_lockin_flags:
                lines.append(f"| `{flag.path}` | {flag.description} |")
            lines.append("")
            lines.append("### Move behind DAL")
            lines.append("")
            for flag in vendor_lockin_flags:
                lines.append(f"- `{flag.path}` — {flag.description}")
            lines.append("")

    tech_debt_path.write_text("\n".join(lines))


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    repo_root = args.repo_root.resolve()

    records, by_extension, secret_flags, gpt2_flags, vendor_lockin_flags = collect_inventory(repo_root)

    artifacts_dir = repo_root / "artifacts"
    inventory_json_path = artifacts_dir / "inventory.json"
    docs_dir = repo_root / "docs"
    inventory_md_path = docs_dir / "INVENTORY.md"
    tech_debt_md_path = docs_dir / "TECH_DEBT.md"

    write_inventory_json(
        inventory_json_path,
        repo_root,
        records,
        by_extension,
        secret_flags,
        gpt2_flags,
        vendor_lockin_flags,
    )
    write_inventory_markdown(
        inventory_md_path,
        repo_root,
        records,
        by_extension,
        secret_flags,
        gpt2_flags,
        vendor_lockin_flags,
    )
    write_tech_debt_markdown(
        tech_debt_md_path,
        secret_flags,
        gpt2_flags,
        vendor_lockin_flags,
    )

    if args.strict and (secret_flags or gpt2_flags or vendor_lockin_flags):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
