from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from dredge.cli import main
from dredge.compiler import BuildError, compile_site


def test_compile_fixture_site_and_query_results(tmp_path: Path) -> None:
    config_path, output_dir = _write_fixture_project(tmp_path)

    result = compile_site(config_path)

    assert result.page_count == 2
    assert result.manifest_path == output_dir / "search-manifest.json"
    assert result.db_path == output_dir / result.manifest["db_file"]
    assert result.manifest["db_sha256"] in result.manifest["db_file"]

    connection = sqlite3.connect(result.db_path)
    try:
        fts_rows = connection.execute(
            """
            SELECT d.url
            FROM documents_fts
            JOIN documents d ON d.id = documents_fts.rowid
            WHERE documents_fts MATCH ?
            ORDER BY d.id
            """,
            ("golden",),
        ).fetchall()
        assert fts_rows == [("/",)]

        filtered_rows = connection.execute(
            "SELECT url FROM documents WHERE category = ? AND year = ?",
            ("guide", 2024),
        ).fetchall()
        assert filtered_rows == [("/",)]

        tag_rows = connection.execute(
            "SELECT value FROM facet_tags WHERE document_id = 1 ORDER BY value"
        ).fetchall()
        assert tag_rows == [("ancient",), ("burial",)]
    finally:
        connection.close()


def test_cli_validate_and_compile(tmp_path: Path) -> None:
    config_path, output_dir = _write_fixture_project(tmp_path)

    assert main(["validate", "--config", str(config_path)]) == 0
    assert main(["compile", "--config", str(config_path)]) == 0
    assert (output_dir / "search-manifest.json").exists()


def test_compile_is_deterministic_for_unchanged_input(tmp_path: Path) -> None:
    config_path, output_dir = _write_fixture_project(tmp_path)

    first = compile_site(config_path)
    first_manifest = first.manifest_path.read_bytes()
    first_db_hash = first.manifest["db_sha256"]

    second = compile_site(config_path)
    second_manifest = second.manifest_path.read_bytes()

    assert second.manifest["db_sha256"] == first_db_hash
    assert second_manifest == first_manifest

    connection = sqlite3.connect(second.db_path)
    try:
        rows = connection.execute("SELECT id, url FROM documents ORDER BY id").fetchall()
    finally:
        connection.close()
    assert rows == [(1, "/"), (2, "/collections/beta/")]


def test_invalid_config_fails_before_output(tmp_path: Path) -> None:
    output_dir = tmp_path / "search"
    config_path = tmp_path / "dredge.config.json"
    config_path.write_text(
        json.dumps({"source_dir": str(tmp_path / "missing"), "output_dir": str(output_dir)}),
        encoding="utf-8",
    )

    with pytest.raises(BuildError) as error:
        compile_site(config_path)

    assert error.value.code == "CONFIG_INVALID"
    assert not output_dir.exists()


def test_missing_required_facet_reports_file_path(tmp_path: Path) -> None:
    config_path, output_dir = _write_fixture_project(
        tmp_path,
        index_attrs="data-dredge-year='2024'",
    )

    with pytest.raises(BuildError) as error:
        compile_site(config_path)

    assert error.value.code == "FACET_REQUIRED_MISSING"
    assert "index.html" in str(error.value)
    assert not (output_dir / "search-manifest.json").exists()


def test_malformed_facet_value_reports_file_path(tmp_path: Path) -> None:
    config_path, output_dir = _write_fixture_project(
        tmp_path,
        index_attrs="data-dredge-category='guide' data-dredge-year='twenty-four'",
    )

    with pytest.raises(BuildError) as error:
        compile_site(config_path)

    assert error.value.code == "FACET_VALUE_INVALID"
    assert "index.html" in str(error.value)
    assert "twenty-four" in str(error.value)
    assert not (output_dir / "search-manifest.json").exists()


def _write_fixture_project(tmp_path: Path, *, index_attrs: str | None = None) -> tuple[Path, Path]:
    source_dir = tmp_path / "site"
    output_dir = tmp_path / "search"
    source_dir.mkdir()
    (source_dir / "collections" / "beta").mkdir(parents=True)

    attrs = index_attrs or "data-dredge-category='guide' data-dredge-year='2024'"
    (source_dir / "index.html").write_text(
        f"""
        <!doctype html>
        <html>
          <head>
            <title>Alpha Tombs</title>
            <meta name="description" content="Guide to alpha tombs">
            <meta property="article:tag" content="ancient">
            <meta property="article:tag" content="burial">
          </head>
          <body>
            <main {attrs}>
              <h1>Alpha Tombs</h1>
              <p>A golden coffin appears in this searchable fixture.</p>
              <script>window.secret = 'not indexed';</script>
            </main>
          </body>
        </html>
        """,
        encoding="utf-8",
    )
    (source_dir / "collections" / "beta" / "index.html").write_text(
        """
        <!doctype html>
        <html>
          <head>
            <title>Beta Collection</title>
            <meta name="description" content="Collection page">
            <meta property="article:tag" content="archive">
          </head>
          <body>
            <main data-dredge-category="collection" data-dredge-year="2023">
              <h1>Beta Collection</h1>
              <p>Catalog records and images.</p>
            </main>
          </body>
        </html>
        """,
        encoding="utf-8",
    )

    config = {
        "source_dir": str(source_dir),
        "output_dir": str(output_dir),
        "base_url": "/",
        "include": ["**/*.html"],
        "exclude": [],
        "selectors": {
            "title": "title, h1",
            "body": "main",
            "description": "meta[name='description']@content",
        },
        "facets": {
            "category": {"type": "string", "source": "data-dredge-category", "required": True},
            "tags": {"type": "string_array", "source": "meta[property='article:tag']@content"},
            "year": {"type": "integer", "source": "data-dredge-year"},
        },
        "result_fields": ["title", "url", "description", "category", "year"],
        "composite_indices": [["category", "year"]],
    }
    config_path = tmp_path / "dredge.config.json"
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return config_path, output_dir
