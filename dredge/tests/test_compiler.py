from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
from pathlib import Path

import brotli
import pytest

from dredge.codegen import generate_client_source
from dredge.cli import main
from dredge.compiler import BuildError, compile_site, load_config
from dredge.query import SearchRequest, build_search_queries, escape_fts_query, search


def test_escape_fts_query_handles_compact_and_spaced_identifiers() -> None:
    assert escape_fts_query("G7510") == '("G7510"* OR "G"* + "7510"*)'
    assert escape_fts_query("G 7510") == '("G7510"* OR "G"* + "7510"*)'
    assert escape_fts_query("A644_NS") == (
        '("A644NS"* OR "A644"* + "NS"* OR "A"* + "644"* + "NS"*)'
    )
    assert escape_fts_query("HUMFA_14-11-206") == (
        '("HUMFA1411206"* OR "HUMFA"* + "14"* + "11"* + "206"*)'
    )


def test_compile_fixture_site_and_query_results(tmp_path: Path) -> None:
    config_path, output_dir = _write_fixture_project(tmp_path)

    result = compile_site(config_path)

    assert result.page_count == 2
    assert result.manifest_path == output_dir / "search-manifest.json"
    assert result.compressed_db_path == output_dir / result.manifest["db_file"]
    assert result.manifest["db_file"].endswith(".db.br")
    assert result.manifest["db_sha256"] in result.manifest["db_file"]
    assert result.manifest["db_compression"] == "brotli"
    assert result.manifest["db_bytes"] == result.db_path.stat().st_size
    assert (
        result.manifest["db_compressed_bytes"]
        == result.compressed_db_path.stat().st_size
    )
    assert "range_required" not in result.manifest
    assert "range_block_bytes" not in result.manifest

    decompressed = brotli.decompress(result.compressed_db_path.read_bytes())
    assert decompressed == result.db_path.read_bytes()
    assert len(decompressed) == result.manifest["db_bytes"]

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


def test_cli_compile_accepts_low_brotli_quality(tmp_path: Path) -> None:
    config_path, output_dir = _write_fixture_project(tmp_path)

    assert (
        main(
            [
                "compile",
                "--config",
                str(config_path),
                "--brotli-quality",
                "1",
            ]
        )
        == 0
    )

    manifest = json.loads(
        (output_dir / "search-manifest.json").read_text(encoding="utf-8")
    )
    compressed_path = output_dir / manifest["db_file"]
    db_path = output_dir / manifest["db_file"].removesuffix(".br")
    assert brotli.decompress(compressed_path.read_bytes()) == db_path.read_bytes()


def test_cli_compile_writes_metrics_json(tmp_path: Path) -> None:
    config_path, _ = _write_fixture_project(tmp_path)
    metrics_path = tmp_path / "metrics.json"

    assert (
        main(
            [
                "compile",
                "--config",
                str(config_path),
                "--metrics-json",
                str(metrics_path),
            ]
        )
        == 0
    )

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert metrics["metrics_version"] == 1
    assert metrics["candidate_count"] == 2
    assert metrics["page_count"] == 2
    assert metrics["ingest"]["documents"] == 2
    assert metrics["ingest"]["documents_per_second"] > 0
    assert metrics["database"]["db_file"].startswith("search.")
    assert metrics["database"]["db_file"].endswith(".db.br")
    assert metrics["database"]["db_compression"] == "brotli"
    assert metrics["database"]["db_compressed_bytes"] > 0
    for phase in (
        "validation",
        "discovery",
        "extraction_ingest",
        "index_creation",
        "fts_optimize",
        "analyze",
        "vacuum_into",
        "hashing",
        "post_build_checks",
        "compression",
        "manifest_write",
    ):
        assert phase in metrics["phases"]
        assert metrics["phases"][phase] >= 0


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
        rows = connection.execute(
            "SELECT id, url FROM documents ORDER BY id"
        ).fetchall()
    finally:
        connection.close()
    assert rows == [(1, "/"), (2, "/collections/beta/")]


def test_final_database_schema_indexes_and_query_plans(tmp_path: Path) -> None:
    config_path, _ = _write_fixture_project(tmp_path)

    result = compile_site(config_path)

    connection = sqlite3.connect(f"file:{result.db_path}?mode=ro&immutable=1", uri=True)
    try:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert connection.execute("PRAGMA page_size").fetchone() == (16_384,)

        fts_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'documents_fts'"
        ).fetchone()[0]
        assert "content=''" in fts_sql

        index_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index' AND name NOT LIKE 'sqlite_autoindex%'"
            )
        }
        assert {
            "documents_category_idx",
            "documents_category_year_idx",
            "documents_featured_idx",
            "documents_published_idx",
            "documents_rating_idx",
            "documents_year_idx",
            "facet_tags_value_document_idx",
        } <= index_names

        assert connection.execute("SELECT COUNT(*) FROM sqlite_stat1").fetchone()[0] > 0

        assert _plan_uses_index(
            connection,
            "SELECT id FROM documents INDEXED BY documents_year_idx WHERE year = ? ORDER BY id",
            (2024,),
            "documents_year_idx",
        )
        assert _plan_uses_index(
            connection,
            """
            SELECT id
            FROM documents INDEXED BY documents_category_year_idx
            WHERE category = ? AND year = ?
            ORDER BY id
            """,
            ("guide", 2024),
            "documents_category_year_idx",
        )
        assert _plan_uses_index(
            connection,
            """
            SELECT document_id
            FROM facet_tags INDEXED BY facet_tags_value_document_idx
            WHERE value = ?
            ORDER BY document_id
            """,
            ("ancient",),
            "facet_tags_value_document_idx",
        )
    finally:
        connection.close()


def test_invalid_config_fails_before_output(tmp_path: Path) -> None:
    output_dir = tmp_path / "search"
    config_path = tmp_path / "dredge.config.json"
    config_path.write_text(
        json.dumps(
            {"source_dir": str(tmp_path / "missing"), "output_dir": str(output_dir)}
        ),
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
        json.dumps(
            {"source_dir": str(tmp_path / "missing"), "output_dir": str(output_dir)}
        ),
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

    description_warnings = [
        warning for warning in result.warnings if warning.field == "description"
    ]
    assert len(description_warnings) == 1
    warning = description_warnings[0]
    assert warning.code == "SELECTOR_MISS"
    assert warning.count == 2
    assert len(warning.sample_paths) == 2
    assert "2 occurrences" in warning.message
    assert "index.html" in warning.message


def test_query_builder_generates_safe_sql_for_all_facet_types(tmp_path: Path) -> None:
    config_path, _ = _write_fixture_project(tmp_path)
    config = load_config(config_path)

    queries = build_search_queries(
        config,
        {
            "query": 'golden" OR category:collection',
            "filters": {
                "category": ["guide", "collection"],
                "featured": True,
                "published": {"max": "2024-12-31"},
                "rating": {"min": 3.0},
                "tags": ["ancient", "archive"],
                "year": {"min": 2023, "max": 2024},
            },
            "limit": 5,
            "offset": 0,
            "includeFacets": True,
        },
    )

    assert "golden" not in queries.results.sql
    assert "category:collection" not in queries.results.sql
    assert "documents_fts MATCH ?" in queries.results.sql
    assert 'd."category" IN (?, ?)' in queries.results.sql
    assert 'd."featured" = ?' in queries.results.sql
    assert 'd."published" <= ?' in queries.results.sql
    assert 'd."rating" >= ?' in queries.results.sql
    assert 'd."year" >= ? AND d."year" <= ?' in queries.results.sql
    assert 'EXISTS (SELECT 1 FROM "facet_tags" af' in queries.results.sql
    assert queries.results.parameters[0] == escape_fts_query(
        'golden" OR category:collection'
    )
    assert set(queries.facets) == {
        "category",
        "featured",
        "published",
        "rating",
        "tags",
        "year",
    }


def test_search_api_handles_empty_search_filtered_search_pagination_and_facets(
    tmp_path: Path,
) -> None:
    config_path, _ = _write_fixture_project(tmp_path)
    config = load_config(config_path)
    result = compile_site(config_path)

    connection = sqlite3.connect(f"file:{result.db_path}?mode=ro&immutable=1", uri=True)
    try:
        empty_page = search(connection, config, SearchRequest(limit=1, offset=1))
        assert empty_page.total == 2
        assert [hit["url"] for hit in empty_page.hits] == ["/collections/beta/"]

        golden = search(
            connection,
            config,
            {
                "query": "golden coffin",
                "filters": {"category": "guide"},
                "includeFacets": ["category", "tags"],
            },
        )
        assert golden.total == 1
        assert golden.hits[0]["url"] == "/"
        assert golden.hits[0]["category"] == "guide"
        assert golden.hits[0]["year"] == 2024
        assert isinstance(golden.hits[0]["score"], float)
        assert golden.facets is not None
        assert [
            (bucket.value, bucket.count) for bucket in golden.facets["category"]
        ] == [("guide", 1)]
        assert {bucket.value for bucket in golden.facets["tags"]} == {
            "ancient",
            "burial",
        }

        filtered = search(
            connection,
            config,
            {
                "filters": {
                    "category": ["collection"],
                    "featured": False,
                    "published": {"min": "2023-01-01", "max": "2023-12-31"},
                    "rating": {"min": 3.0, "max": 4.0},
                    "tags": "archive",
                    "year": 2023,
                }
            },
        )
        assert filtered.total == 1
        assert filtered.hits[0]["url"] == "/collections/beta/"
    finally:
        connection.close()


def test_search_indexes_extra_fields_and_matches_identifier_variants(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "site"
    output_dir = tmp_path / "search"
    source_dir.mkdir()
    (source_dir / "sites" / "172" / "full").mkdir(parents=True)
    (source_dir / "photos" / "20541" / "full").mkdir(parents=True)
    (source_dir / "sites" / "172" / "full" / "index.html").write_text(
        """
        <!doctype html>
        <html>
        <head>
          <title>G 7510</title>
          <meta name="description" content="Eastern Cemetery tomb">
          <meta data-pagefind-meta="category[content]" content="Tombs and Monuments">
          <meta data-pagefind-meta="catalog_id[content]" content="G 7510">
          <meta data-pagefind-meta="searchtext[content]" content="G 7510 G7510">
        </head>
        <body><main data-pagefind-body><h1>G 7510</h1></main></body>
        </html>
        """,
        encoding="utf-8",
    )
    (source_dir / "photos" / "20541" / "full" / "index.html").write_text(
        """
        <!doctype html>
        <html>
        <head>
          <title>Western Cemetery photo</title>
          <meta name="description" content="Photo record">
          <meta data-pagefind-meta="category[content]" content="Photos">
          <meta data-pagefind-meta="catalog_id[content]" content="HUMFA_A644_NS">
          <meta data-pagefind-meta="searchtext[content]" content="HUMFA_A644_NS A644_NS HUMFAA644NS A644">
        </head>
        <body><main data-pagefind-body><h1>Western Cemetery photo</h1></main></body>
        </html>
        """,
        encoding="utf-8",
    )
    config_path = tmp_path / "dredge.config.json"
    config_path.write_text(
        json.dumps(
            {
                "source_dir": str(source_dir),
                "output_dir": str(output_dir),
                "base_url": "/",
                "include": ["**/full/index.html"],
                "selectors": {
                    "title": "meta[data-pagefind-meta='title[content]']@content",
                    "body": "[data-pagefind-body]",
                    "description": "meta[name='description']@content",
                },
                "search_fields": [
                    "meta[data-pagefind-meta='catalog_id[content]']@content",
                    "meta[data-pagefind-meta='searchtext[content]']@content",
                ],
                "facets": {
                    "category": {
                        "type": "string",
                        "source": "meta[data-pagefind-meta='category[content]']@content",
                    },
                    "catalog_id": {
                        "type": "string",
                        "source": "meta[data-pagefind-meta='catalog_id[content]']@content",
                    },
                },
                "result_fields": [
                    "title",
                    "url",
                    "description",
                    "category",
                    "catalog_id",
                ],
            }
        ),
        encoding="utf-8",
    )
    config = load_config(config_path)
    result = compile_site(config_path)

    connection = sqlite3.connect(f"file:{result.db_path}?mode=ro&immutable=1", uri=True)
    try:
        compact_tomb = search(connection, config, {"query": "G7510"})
        spaced_tomb = search(connection, config, {"query": "G 7510"})
        photo = search(connection, config, {"query": "A644_NS"})
    finally:
        connection.close()

    assert compact_tomb.total == 1
    assert compact_tomb.hits[0]["catalog_id"] == "G 7510"
    assert spaced_tomb.total == 1
    assert spaced_tomb.hits[0]["catalog_id"] == "G 7510"
    assert photo.total == 1
    assert photo.hits[0]["catalog_id"] == "HUMFA_A644_NS"


def test_compile_writes_generated_types_worker_protocol_and_stale_handling(
    tmp_path: Path,
) -> None:
    client_path = tmp_path / "src" / "dredge-client.ts"
    config_path, _ = _write_fixture_project(
        tmp_path,
        client={
            "out": str(client_path),
            "worker_url": "/search/dredge-worker.abc123.js",
        },
    )

    result = compile_site(config_path)

    assert result.client_path == client_path
    source = client_path.read_text(encoding="utf-8")
    assert "export interface DredgeFilters" in source
    assert "category?: string | string[];" in source
    assert "tags?: string | string[];" in source
    assert "year?: number | number[] | DredgeRange<number>;" in source
    assert "published?: string | string[] | DredgeRange<string>;" in source
    assert "export type DredgeWorkerRequest" in source
    assert "export type DredgeWorkerResponse" in source
    assert "rejectOlderSearches" in source
    assert "STALE_RESPONSE" in source
    assert 'const DEFAULT_WORKER_URL = "/search/dredge-worker.abc123.js";' in source


def test_pagefind_compatible_attributes_extract_and_ignore_content(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "site"
    output_dir = tmp_path / "search"
    source_dir.mkdir()
    (source_dir / "index.html").write_text(
        """
        <!doctype html>
        <html>
        <head>
          <title>Fallback Title</title>
          <meta name="description" content="Catalog description">
          <meta data-pagefind-meta="catalog_id[content]" content="abc-123">
          <meta data-pagefind-sort="title[content]" content="Pagefind Title">
        </head>
        <body>
          <h1 data-pagefind-body>Pagefind Title</h1>
          <p data-pagefind-body>Visible golden content.</p>
          <div data-pagefind-ignore>Ignored secret content.</div>
          <div aria-hidden="true"><span data-pagefind-filter="category">Objects</span></div>
        </body>
        </html>
        """,
        encoding="utf-8",
    )
    config_path = tmp_path / "dredge.config.json"
    config_path.write_text(
        json.dumps(
            {
                "source_dir": str(source_dir),
                "output_dir": str(output_dir),
                "selectors": {
                    "title": "h1[data-pagefind-body]",
                    "body": "body",
                    "description": "meta[name='description']@content",
                },
                "facets": {
                    "catalog_id": {
                        "type": "string",
                        "source": "meta[data-pagefind-meta='catalog_id[content]']@content",
                    },
                    "category": {
                        "type": "string",
                        "source": "[data-pagefind-filter='category']",
                    },
                    "sort_title": {
                        "type": "string",
                        "source": "meta[data-pagefind-sort='title[content]']@content",
                    },
                },
                "result_fields": [
                    "title",
                    "url",
                    "description",
                    "category",
                    "catalog_id",
                    "sort_title",
                ],
            }
        ),
        encoding="utf-8",
    )

    result = compile_site(config_path)

    connection = sqlite3.connect(result.db_path)
    try:
        assert connection.execute(
            "SELECT title, category, catalog_id, sort_title FROM documents"
        ).fetchone() == (
            "Pagefind Title",
            "Objects",
            "abc-123",
            "Pagefind Title",
        )
        assert connection.execute(
            "SELECT COUNT(*) FROM documents_fts WHERE documents_fts MATCH ?",
            ("golden",),
        ).fetchone() == (1,)
        assert connection.execute(
            "SELECT COUNT(*) FROM documents_fts WHERE documents_fts MATCH ?",
            ("secret",),
        ).fetchone() == (0,)
    finally:
        connection.close()


def test_codegen_cli_requires_client_output(tmp_path: Path) -> None:
    config_path, _ = _write_fixture_project(tmp_path)

    assert main(["codegen", "--config", str(config_path)]) == 1


def test_generated_client_typechecks_fixture_app_with_pnpm(tmp_path: Path) -> None:
    pnpm = shutil.which("pnpm")
    if pnpm is None:
        pytest.skip("pnpm is not installed")

    client_path = tmp_path / "dredge-client.ts"
    config_path, _ = _write_fixture_project(tmp_path, client={"out": str(client_path)})
    config = load_config(config_path)
    client_path.write_text(generate_client_source(config), encoding="utf-8")
    app_path = tmp_path / "fixture-app.ts"
    app_path.write_text(
        """
        import { DredgeSearchClient, type DredgeSearchRequest } from "./dredge-client";

        const client = new DredgeSearchClient({ workerUrl: "/search/dredge-worker.js" });
        const request: DredgeSearchRequest = {
          query: "golden",
          filters: {
            category: ["guide", "collection"],
            featured: false,
            published: { min: "2023-01-01", max: "2024-12-31" },
            rating: { min: 3, max: 5 },
            tags: "ancient",
            year: { min: 2023, max: 2024 },
          },
          includeFacets: ["category", "tags"],
        };

        async function runSearch() {
          const response = await client.search(request);
          const firstTitle: string | undefined = response.hits[0]?.title;
          return firstTitle;
        }

        void runSearch();
        """,
        encoding="utf-8",
    )

    subprocess.run(
        [
            pnpm,
            "dlx",
            "--package",
            "typescript",
            "tsc",
            "--strict",
            "--target",
            "ES2020",
            "--lib",
            "ES2020,DOM",
            "--noEmit",
            str(app_path),
        ],
        check=True,
    )


def _plan_uses_index(
    connection: sqlite3.Connection,
    sql: str,
    parameters: tuple[object, ...],
    index_name: str,
) -> bool:
    details = [
        str(row[3])
        for row in connection.execute(f"EXPLAIN QUERY PLAN {sql}", parameters)
    ]
    return any(
        "SEARCH" in detail.upper() and index_name in detail for detail in details
    )


def _write_fixture_project(
    tmp_path: Path,
    *,
    index_attrs: str | None = None,
    include_descriptions: bool = True,
    client: dict[str, str] | None = None,
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
    index_description = (
        '<meta name="description" content="Guide to alpha tombs">'
        if include_descriptions
        else ""
    )
    beta_description = (
        '<meta name="description" content="Collection page">'
        if include_descriptions
        else ""
    )
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
            "category": {
                "type": "string",
                "source": "data-dredge-category",
                "required": True,
            },
            "featured": {"type": "boolean", "source": "data-dredge-featured"},
            "published": {"type": "date", "source": "data-dredge-published"},
            "rating": {"type": "number", "source": "data-dredge-rating"},
            "tags": {
                "type": "string_array",
                "source": "meta[property='article:tag']@content",
            },
            "year": {"type": "integer", "source": "data-dredge-year"},
        },
        "result_fields": ["title", "url", "description", "category", "year"],
        "composite_indices": [["category", "year"]],
    }
    if client is not None:
        config["client"] = client
    config_path = tmp_path / "dredge.config.json"
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return config_path, output_dir
