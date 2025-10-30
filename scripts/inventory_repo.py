#!/usr/bin/env python3
"""Repository inventory and legacy scanner for Week 1 bootstrap."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

CRITICAL_FLAGS = {
    "mentions_gpt2": "Found GPT-2 reference in default code path",
    "has_api_key_pattern": "Potential secret committed to the repository",
}
SOFT_FLAGS = {
    "is_ipynb": ".ipynb notebook present",
    "mentions_clip": "CLIP mention",
    "mentions_whisper": "Whisper mention",
    "mentions_deepseek": "DeepSeek mention",
}
ALL_FLAGS = {**CRITICAL_FLAGS, **SOFT_FLAGS}

API_KEY_RE = re.compile(r"(?:sk-|AIza|AKIA|ghp_)[A-Za-z0-9_-]{10,}")
BINARY_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bin", ".pt", ".safetensors", ".gguf"}
LANGUAGE_MAP = {
    ".py": "python",
    ".ipynb": "ipynb",
    ".md": "markdown",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".txt": "text",
}
SKIP_DIR_NAMES = {".git", "artifacts", ".github/cache", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache"}
THIS_FILE = Path(__file__).resolve()


def sha10(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()[:10]


def language_of(path: Path) -> str:
    return LANGUAGE_MAP.get(path.suffix.lower(), mimetypes.guess_type(path.name)[0] or "other")


def should_skip_dir(path: Path) -> bool:
    return any(part in SKIP_DIR_NAMES for part in path.parts)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except (UnicodeDecodeError, OSError):
        return ""


def detect_flags(path: Path, text: str) -> Dict[str, bool]:
    lower = text.lower()
    return {
        "is_ipynb": path.suffix.lower() == ".ipynb",
        "mentions_gpt2": "gpt2" in lower,
        "mentions_clip": "clip" in lower,
        "mentions_whisper": "whisper" in lower,
        "mentions_deepseek": "deepseek" in lower,
        "has_api_key_pattern": bool(API_KEY_RE.search(text)),
    }


def scan_repo(root: Path) -> List[Dict[str, object]]:
    entries: List[Dict[str, object]] = []
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        dirnames[:] = [d for d in dirnames if not should_skip_dir(current / d)]
        for filename in filenames:
            file_path = current / filename
            rel_path = file_path.relative_to(root).as_posix()
            try:
                size = file_path.stat().st_size
            except OSError:
                continue

            text = ""
            if file_path.suffix.lower() not in BINARY_EXTENSIONS and size <= 2_000_000:
                text = read_text(file_path)

            flags = detect_flags(file_path, text)
            if file_path.resolve() == THIS_FILE:
                flags["mentions_gpt2"] = False
            entries.append(
                {
                    "path": rel_path,
                    "size": size,
                    "sha": sha10(file_path),
                    "lang": language_of(file_path),
                    "flags": flags,
                }
            )
    return entries


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_inventory_json(entries: Sequence[Dict[str, object]], output_path: Path) -> None:
    ensure_directory(output_path.parent)
    output_path.write_text(json.dumps(entries, indent=2))


def write_inventory_md(entries: Sequence[Dict[str, object]], output_path: Path) -> None:
    ensure_directory(output_path.parent)
    lines: List[str] = ["# Repo Inventory (auto-generated)", ""]
    lines.append(f"Total files: {len(entries)}")
    total_bytes = sum(entry["size"] for entry in entries)  # type: ignore[arg-type]
    lines.append(f"Total size: {total_bytes} bytes")
    lines.append("")

    counts = Counter(entry["lang"] for entry in entries)  # type: ignore[index]
    lines.append("## Counts by language")
    for lang, count in counts.most_common():
        lines.append(f"- {lang}: {count}")
    lines.append("")

    flag_map: Dict[str, List[str]] = {key: [] for key in ALL_FLAGS}
    for entry in entries:
        path = entry["path"]  # type: ignore[index]
        flags = entry["flags"]  # type: ignore[index]
        for name, enabled in flags.items():
            if enabled:
                flag_map.setdefault(name, []).append(path)

    lines.append("## Flagged files")
    lines.append("")
    for name, description in ALL_FLAGS.items():
        files = flag_map.get(name, [])
        if not files:
            continue
        lines.append(f"### {name} — {description} ({len(files)})")
        for rel_path in sorted(files)[:200]:
            lines.append(f"- `{rel_path}`")
        lines.append("")
    if lines[-1] != "":
        lines.append("")

    top_100 = sorted(entries, key=lambda entry: entry["size"], reverse=True)[:100]  # type: ignore[index]
    lines.append("## Top 100 files by size")
    lines.append("")
    lines.append("| Path | Size (bytes) |")
    lines.append("| --- | ---: |")
    for entry in top_100:
        lines.append(f"| `{entry['path']}` | {entry['size']} |")
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def write_tech_debt_md(entries: Sequence[Dict[str, object]], output_path: Path) -> None:
    ensure_directory(output_path.parent)
    lines: List[str] = ["# TECH_DEBT (auto-generated)", ""]

    flag_summary: Dict[str, List[str]] = {key: [] for key in ALL_FLAGS}
    for entry in entries:
        path = entry["path"]  # type: ignore[index]
        flags = entry["flags"]  # type: ignore[index]
        for name, enabled in flags.items():
            if enabled:
                flag_summary.setdefault(name, []).append(path)

    if not any(flag_summary.values()):
        lines.append("- No flagged items detected.")
    else:
        if flag_summary["mentions_gpt2"]:
            lines.append("- Replace GPT-2 references with student Llama-3.2-3B / Qwen-2.5-3B configs (Week 10/11 plan).")
        if flag_summary["has_api_key_pattern"]:
            lines.append("- Remove committed secrets and store credentials in environment variables or secret managers.")
        if flag_summary["is_ipynb"]:
            lines.append("- Migrate critical notebooks to scripted workflows or ensure they are optional for CI.")
        if flag_summary["mentions_clip"]:
            lines.append("- Confirm CLIP usage aligns with current vision stack; document migration path if deprecated.")
        if flag_summary["mentions_whisper"]:
            lines.append("- Validate Whisper models meet latency targets and document batching strategies.")
        if flag_summary["mentions_deepseek"]:
            lines.append("- Audit DeepSeek dependencies for maintenance status and compliance risks.")

        lines.append("")
        for name, files in flag_summary.items():
            if not files:
                continue
            lines.append(f"## {name} ({len(files)})")
            for rel_path in sorted(files)[:200]:
                lines.append(f"- `{rel_path}`")
            lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def run(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate inventory artifacts and docs.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if critical flags are detected.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    repo_root = Path.cwd()
    entries = scan_repo(repo_root)

    write_inventory_json(entries, repo_root / "artifacts" / "inventory.json")
    write_inventory_md(entries, repo_root / "docs" / "INVENTORY.md")
    write_tech_debt_md(entries, repo_root / "docs" / "TECH_DEBT.md")

    if args.strict:
        offending: List[str] = []
        for entry in entries:
            flags = entry["flags"]  # type: ignore[index]
            path = str(entry["path"])  # type: ignore[index]
            for name in CRITICAL_FLAGS:
                if not flags.get(name):
                    continue
                if name == "mentions_gpt2" and (
                    path.endswith((".md", ".ipynb", ".yaml", ".yml", ".json"))
                    or path.startswith("docs/")
                    or path.startswith("colab_notebooks/")
                ):
                    continue
                offending.append(f"{name}: {path}")
        if offending:
            print("CRITICAL flags detected:")
            for item in offending:
                print(f"- {item}")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
