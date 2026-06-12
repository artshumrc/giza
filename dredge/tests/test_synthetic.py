from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from dredge.compiler import compile_site, load_config
from dredge.synthetic import generate_site


def test_generate_site_is_deterministic(tmp_path: Path) -> None:
    first = generate_site(tmp_path / "a", count=25, seed=7)
    second = generate_site(tmp_path / "b", count=25, seed=7)

    first_pages = sorted(first.source_dir.rglob("*.html"))
    second_pages = sorted(second.source_dir.rglob("*.html"))
    assert len(first_pages) == 25
    assert len(second_pages) == 25

    for left, right in zip(first_pages, second_pages, strict=True):
        assert left.read_text(encoding="utf-8") == right.read_text(encoding="utf-8")


def test_generated_site_compiles_and_queries(tmp_path: Path) -> None:
    site = generate_site(tmp_path, count=50, seed=3)

    config = load_config(site.config_path)
    assert config.source_dir == site.source_dir

    result = compile_site(site.config_path)
    assert result.page_count == 50
    assert result.manifest["db_file"].endswith(".db.br")

    connection = sqlite3.connect(f"file:{result.db_path}?mode=ro&immutable=1", uri=True)
    try:
        total = connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        assert total == 50

        categories = connection.execute(
            "SELECT DISTINCT category FROM documents"
        ).fetchall()
        assert all(row[0] is not None for row in categories)

        matches = connection.execute(
            "SELECT COUNT(*) FROM documents_fts WHERE documents_fts MATCH ?",
            ("ancient",),
        ).fetchone()[0]
        assert matches > 0
    finally:
        connection.close()


def test_generate_site_rejects_zero_count(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        generate_site(tmp_path, count=0)
