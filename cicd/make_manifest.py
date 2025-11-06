"""Utility for building a release manifest of model and stats assets.

The script walks the model and stats directories, computes file sizes and
SHA256 hashes for each file, and writes the information to a JSON manifest.

The default directories assume the repository layout of
``rayskillkit/skills/{models,stats}``, but callers can override them through the
CLI flags so CI jobs can point to temporary locations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Dict, Iterable, List


def _iter_files(directory: Path) -> Iterable[Path]:
    if not directory.exists():
        raise FileNotFoundError(f"Directory does not exist: {directory}")

    for path in sorted(directory.rglob("*")):
        if path.is_file():
            yield path


def _file_entry(path: Path, base_dir: Path) -> Dict[str, object]:
    sha256 = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            if not chunk:
                break
            sha256.update(chunk)

    return {
        "path": str(path.relative_to(base_dir)),
        "sha256": sha256.hexdigest(),
        "size": path.stat().st_size,
    }


def build_manifest(models_dir: Path, stats_dir: Path) -> Dict[str, List[Dict[str, object]]]:
    models = [_file_entry(path, models_dir) for path in _iter_files(models_dir)]
    stats = [_file_entry(path, stats_dir) for path in _iter_files(stats_dir)]
    return {"models": models, "stats": stats}


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    default_models = repo_root / "rayskillkit" / "skills" / "models"
    default_stats = repo_root / "rayskillkit" / "skills" / "stats"
    default_output = repo_root / "release_manifest.json"

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--models-dir",
        type=Path,
        default=default_models,
        help=f"Directory containing model artifacts (default: {default_models})",
    )
    parser.add_argument(
        "--stats-dir",
        type=Path,
        default=default_stats,
        help=f"Directory containing stats artifacts (default: {default_stats})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
        help=f"Path of the manifest JSON to write (default: {default_output})",
    )
    return parser.parse_args(argv)


def write_manifest(manifest: Dict[str, List[Dict[str, object]]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")


def main(argv: Iterable[str] | None = None) -> None:
    args = parse_args(argv)
    manifest = build_manifest(args.models_dir, args.stats_dir)
    write_manifest(manifest, args.output)


if __name__ == "__main__":
    main()
