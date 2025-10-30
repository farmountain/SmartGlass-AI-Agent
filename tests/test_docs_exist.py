from __future__ import annotations

from pathlib import Path


def test_docs_directory_and_week1_doc_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    docs_dir = root / "docs"
    week1_doc = docs_dir / "WEEK_01.md"

    assert docs_dir.is_dir(), "Expected docs/ directory to exist"
    assert week1_doc.is_file(), "Expected Week 1 documentation to exist"
