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

        typed_facet_rows = connection.execute(
            "SELECT rating, featured, published FROM documents WHERE id = 1"
        ).fetchall()
        assert typed_facet_rows == [(4.5, 1, "2024-01-30")]

        tag_rows = connection.execute(
            "SELECT value FROM facet_tags WHERE document_id = 1 ORDER BY value"
        ).fetchall()
        assert tag_rows == [("ancient",), ("burial",)]

        script_rows = connection.execute(
            """
            SELECT d.url
            FROM documents_fts
            JOIN documents d ON d.id = documents_fts.rowid
            WHERE documents_fts MATCH ?
            """,
            ("secret",),
        ).fetchall()
        assert script_rows == []
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


def test_cli_validate_invalid_config_fails_before_output(tmp_path: Path) -> None:
    output_dir = tmp_path / "search"
    config_path = tmp_path / "dredge.config.json"
    config_path.write_text(
        json.dumps({"source_dir": str(tmp_path / "missing"), "output_dir": str(output_dir)}),
        encoding="utf-8",
    )

    assert main(["validate", "--config", str(config_path)]) == 1
    assert not output_dir.exists()


def test_missing_required_facet_reports_file_path(tmp_path: Path) -> None:
    config_path, output_dir = _write_fixture_project(
        tmp_path,
        index_attrs="data-dredge-year='2024'",
    )

    with pytest.raises(BuildError) as error:
        compile_site(config_path)

    assert error.value.code == "FACET_REQUIRED_MISSING"
    assert error.value.path is not None
    assert error.value.path.name == "index.html"
    assert error.value.field == "category"
    assert error.value.selector == "data-dredge-category"
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
    assert error.value.path is not None
    assert error.value.path.name == "index.html"
    assert error.value.field == "year"
    assert error.value.selector == "data-dredge-year"
    assert error.value.value == "twenty-four"
    assert "index.html" in str(error.value)
    assert "twenty-four" in str(error.value)
    assert not (output_dir / "search-manifest.json").exists()


def test_selector_warnings_are_aggregated_with_samples(tmp_path: Path) -> None:
    config_path, _ = _write_fixture_project(tmp_path, include_descriptions=False)

    result = compile_site(config_path)

    description_warnings = [warning for warning in result.warnings if warning.field == "description"]
    assert len(description_warnings) == 1
    warning = description_warnings[0]
    assert warning.code == "SELECTOR_MISS"
    assert warning.count == 2
    assert len(warning.sample_paths) == 2
    assert "2 occurrences" in warning.message
    assert "index.html" in warning.message


def _write_fixture_project(
    tmp_path: Path,
    *,
    index_attrs: str | None = None,
    include_descriptions: bool = True,
) -> tuple[Path, Path]:
    source_dir = tmp_path / "site"
    output_dir = tmp_path / "search"
    source_dir.mkdir()
    (source_dir / "collections" / "beta").mkdir(parents=True)

    attrs = index_attrs or (
        "data-dredge-category='guide' "
        "data-dredge-year='2024' "
        "data-dredge-rating='4.5' "
        "data-dredge-featured='yes' "
        "data-dredge-published='2024-01-30'"
    )
    index_description = '<meta name="description" content="Guide to alpha tombs">' if include_descriptions else ""
    beta_description = '<meta name="description" content="Collection page">' if include_descriptions else ""
    (source_dir / "index.html").write_text(
        f"""
        <!doctype html>
        <html>
          <head>
            <title>Alpha Tombs</title>
            {index_description}
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
        f"""
        <!doctype html>
        <html>
          <head>
            <title>Beta Collection</title>
            {beta_description}
            <meta property="article:tag" content="archive">
          </head>
          <body>
            <main
              data-dredge-category="collection"
              data-dredge-year="2023"
              data-dredge-rating="3.25"
              data-dredge-featured="false"
              data-dredge-published="2023-11-02"
            >
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
            "featured": {"type": "boolean", "source": "data-dredge-featured"},
            "published": {"type": "date", "source": "data-dredge-published"},
            "rating": {"type": "number", "source": "data-dredge-rating"},
            "tags": {"type": "string_array", "source": "meta[property='article:tag']@content"},
            "year": {"type": "integer", "source": "data-dredge-year"},
        },
        "result_fields": ["title", "url", "description", "category", "year"],
        "composite_indices": [["category", "year"]],
    }
    config_path = tmp_path / "dredge.config.json"
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return config_path, output_dir
