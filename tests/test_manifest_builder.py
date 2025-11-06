import hashlib
import json
from pathlib import Path

from cicd.make_manifest import build_manifest, main


def _write_dummy_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _expected_entry(path: Path, base_dir: Path) -> dict:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "path": str(path.relative_to(base_dir)),
        "sha256": digest,
        "size": path.stat().st_size,
    }


def test_build_manifest_returns_expected_structure(tmp_path: Path) -> None:
    models_dir = tmp_path / "models"
    stats_dir = tmp_path / "stats"

    model_file = models_dir / "model.bin"
    stats_file = stats_dir / "stats.json"

    _write_dummy_file(model_file, b"model-contents")
    _write_dummy_file(stats_file, b"{\"stats\": true}")

    manifest = build_manifest(models_dir, stats_dir)

    assert manifest == {
        "models": [_expected_entry(model_file, models_dir)],
        "stats": [_expected_entry(stats_file, stats_dir)],
    }


def test_cli_writes_manifest_file(tmp_path: Path) -> None:
    models_dir = tmp_path / "skills" / "models"
    stats_dir = tmp_path / "skills" / "stats"
    output_path = tmp_path / "artifacts" / "release_manifest.json"

    model_a = models_dir / "nested" / "a.bin"
    model_b = models_dir / "b.bin"
    stats_file = stats_dir / "stats.csv"

    _write_dummy_file(model_a, b"alpha")
    _write_dummy_file(model_b, b"bravo")
    _write_dummy_file(stats_file, b"charlie")

    argv = [
        "--models-dir",
        str(models_dir),
        "--stats-dir",
        str(stats_dir),
        "--output",
        str(output_path),
    ]
    main(argv)

    with output_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    expected_models = sorted(
        [_expected_entry(model_a, models_dir), _expected_entry(model_b, models_dir)],
        key=lambda item: item["path"],
    )
    expected_stats = [_expected_entry(stats_file, stats_dir)]

    assert sorted(data["models"], key=lambda item: item["path"]) == expected_models
    assert data["stats"] == expected_stats
