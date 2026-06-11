from __future__ import annotations

import fnmatch
import hashlib
import json
import re
import shutil
import sqlite3
import tempfile
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from . import __version__

DB_SCHEMA_VERSION = 1
MANIFEST_VERSION = 1
SQLITE_PAGE_SIZE = 16_384
RANGE_BLOCK_BYTES = 65_536
BATCH_SIZE = 10_000

IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
ATTRIBUTE_RE = re.compile(r"^[A-Za-z_:][-A-Za-z0-9_:.]*$")
TOKEN_RE = re.compile(r"[\w]+", re.UNICODE)

TOP_LEVEL_KEYS = {
    "$schema",
    "source_dir",
    "output_dir",
    "base_url",
    "include",
    "exclude",
    "selectors",
    "facets",
    "result_fields",
    "composite_indices",
    "client",
    "allow_output_in_source",
}
SELECTOR_KEYS = {"title", "body", "description"}
FACET_KEYS = {"type", "source", "required"}
CLIENT_KEYS = {"out", "worker_url"}
FACET_TYPES = {"string", "string_array", "integer", "number", "boolean", "date"}
SCALAR_SQL_TYPES = {
    "string": "TEXT",
    "integer": "INTEGER",
    "number": "REAL",
    "boolean": "INTEGER",
    "date": "TEXT",
}


class BuildError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class BuildWarning:
    code: str
    message: str
    path: Path | None = None
    field: str | None = None
    selector: str | None = None


@dataclass(frozen=True)
class FacetConfig:
    name: str
    type: str
    source: str
    required: bool = False

    @property
    def is_array(self) -> bool:
        return self.type == "string_array"


@dataclass(frozen=True)
class DredgeConfig:
    path: Path
    raw: dict[str, Any]
    source_dir: Path
    output_dir: Path
    base_url: str
    include: tuple[str, ...]
    exclude: tuple[str, ...]
    selectors: dict[str, str]
    facets: tuple[FacetConfig, ...]
    result_fields: tuple[str, ...]
    composite_indices: tuple[tuple[str, ...], ...]
    client: dict[str, str]
    allow_output_in_source: bool
    config_hash: str

    @property
    def facet_map(self) -> dict[str, FacetConfig]:
        return {facet.name: facet for facet in self.facets}

    @property
    def scalar_facets(self) -> tuple[FacetConfig, ...]:
        return tuple(facet for facet in self.facets if not facet.is_array)

    @property
    def array_facets(self) -> tuple[FacetConfig, ...]:
        return tuple(facet for facet in self.facets if facet.is_array)


@dataclass(frozen=True)
class FileCandidate:
    path: Path
    rel_path: str
    url: str


@dataclass(frozen=True)
class SkippedFile:
    path: Path
    reason: str


@dataclass
class ExtractedDocument:
    id: int
    url: str
    title: str
    description: str | None
    body: str
    content_hash: str
    scalar_facets: dict[str, str | int | float | None]
    array_facets: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class CompileResult:
    db_path: Path
    manifest_path: Path
    manifest: dict[str, Any]
    page_count: int
    warnings: tuple[BuildWarning, ...] = field(default_factory=tuple)
    skipped: tuple[SkippedFile, ...] = field(default_factory=tuple)


def load_config(config_path: Path) -> DredgeConfig:
    path = _absolute_path(config_path)
    if not path.exists():
        raise BuildError("CONFIG_NOT_FOUND", f"configuration file does not exist: {path}")

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise BuildError(
            "CONFIG_INVALID_JSON",
            f"invalid JSON in {path}: line {error.lineno}, column {error.colno}: {error.msg}",
        ) from error

    if not isinstance(raw, dict):
        raise BuildError("CONFIG_INVALID", f"configuration root must be an object: {path}")

    unknown = sorted(set(raw) - TOP_LEVEL_KEYS)
    if unknown:
        raise BuildError("CONFIG_INVALID", f"unknown configuration key(s): {', '.join(unknown)}")

    base_dir = path.parent
    source_dir = _required_path(raw, "source_dir", base_dir)
    output_dir = _required_path(raw, "output_dir", base_dir)

    if not source_dir.exists() or not source_dir.is_dir():
        raise BuildError("CONFIG_INVALID", f"source_dir must be an existing directory: {source_dir}")

    allow_output_in_source = _optional_bool(raw, "allow_output_in_source", False)
    if _same_or_child(output_dir, source_dir) and not allow_output_in_source:
        raise BuildError(
            "CONFIG_INVALID",
            "output_dir must be outside source_dir unless allow_output_in_source is true: "
            f"source_dir={source_dir}, output_dir={output_dir}",
        )

    base_url = _optional_string(raw, "base_url", "/")
    include = tuple(_optional_string_list(raw, "include", ["**/*.html"]))
    exclude = tuple(_optional_string_list(raw, "exclude", []))
    selectors = _load_selectors(raw)
    facets = _load_facets(raw)
    facet_map = {facet.name: facet for facet in facets}
    result_fields = tuple(_optional_string_list(raw, "result_fields", ["title", "url", "description"]))
    _validate_result_fields(result_fields, facet_map)
    composite_indices = tuple(_load_composite_indices(raw, facet_map))
    client = _load_client(raw)

    effective_config = {
        "$schema": raw.get("$schema"),
        "source_dir": raw["source_dir"],
        "output_dir": raw["output_dir"],
        "base_url": base_url,
        "include": list(include),
        "exclude": list(exclude),
        "selectors": selectors,
        "facets": {
            facet.name: {"type": facet.type, "source": facet.source, "required": facet.required}
            for facet in facets
        },
        "result_fields": list(result_fields),
        "composite_indices": [list(index) for index in composite_indices],
        "client": client,
        "allow_output_in_source": allow_output_in_source,
    }
    config_hash = _sha256_text(json.dumps(effective_config, ensure_ascii=False, sort_keys=True, separators=(",", ":")))

    return DredgeConfig(
        path=path,
        raw=raw,
        source_dir=source_dir,
        output_dir=output_dir,
        base_url=base_url,
        include=include,
        exclude=exclude,
        selectors=selectors,
        facets=facets,
        result_fields=result_fields,
        composite_indices=composite_indices,
        client=client,
        allow_output_in_source=allow_output_in_source,
        config_hash=config_hash,
    )


def check_sqlite_capabilities() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE VIRTUAL TABLE dredge_fts_check USING fts5(body)")
    except sqlite3.OperationalError as error:
        raise BuildError(
            "SQLITE_FTS5_UNAVAILABLE",
            "the active Python sqlite3 build does not support FTS5; use a Python build linked "
            "against SQLite with FTS5 enabled",
        ) from error

    try:
        connection.execute("CREATE TABLE dredge_strict_check(value TEXT) STRICT")
    except sqlite3.OperationalError as error:
        raise BuildError(
            "SQLITE_STRICT_UNAVAILABLE",
            "the active Python sqlite3 build does not support SQLite STRICT tables",
        ) from error
    finally:
        connection.close()


def discover_html_files(config: DredgeConfig) -> tuple[tuple[FileCandidate, ...], tuple[SkippedFile, ...]]:
    candidates: list[FileCandidate] = []
    skipped: list[SkippedFile] = []
    seen_urls: dict[str, Path] = {}
    output_inside_source = _same_or_child(config.output_dir, config.source_dir)

    for path in sorted(config.source_dir.rglob("*"), key=lambda found: found.relative_to(config.source_dir).as_posix()):
        if path.is_dir():
            continue
        rel_path = path.relative_to(config.source_dir).as_posix()

        if path.is_symlink():
            skipped.append(SkippedFile(path=path, reason="symlink"))
            continue

        if output_inside_source and _same_or_child(path, config.output_dir):
            skipped.append(SkippedFile(path=path, reason="output_dir"))
            continue

        if not _matches_any(rel_path, config.include):
            continue

        if _matches_any(rel_path, config.exclude):
            skipped.append(SkippedFile(path=path, reason="excluded"))
            continue

        url = _canonical_url(config.base_url, rel_path)
        if url in seen_urls:
            raise BuildError(
                "DISCOVERY_DUPLICATE_URL",
                f"multiple HTML files resolve to URL {url!r}: {seen_urls[url]} and {path}",
            )
        seen_urls[url] = path
        candidates.append(FileCandidate(path=path, rel_path=rel_path, url=url))

    return tuple(sorted(candidates, key=lambda candidate: (candidate.url, candidate.rel_path))), tuple(skipped)


def compile_site(config_path: Path) -> CompileResult:
    config = load_config(config_path)
    check_sqlite_capabilities()
    candidates, skipped = discover_html_files(config)
    if not candidates:
        raise BuildError("DISCOVERY_NO_FILES", f"no HTML files matched include/exclude patterns in {config.source_dir}")

    config.output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix=".dredge-build-", dir=config.output_dir))
    build_db_path = temp_dir / "build.db"
    compact_db_path = temp_dir / "compact.db"
    warnings: list[BuildWarning] = []

    try:
        smoke_token: str | None = None
        smoke_filter: tuple[str, str, str | int | float] | None = None
        connection = sqlite3.connect(build_db_path)
        try:
            _configure_build_database(connection)
            _create_schema(connection, config)
            insert_sql = _document_insert_sql(config)
            array_insert_sql = {
                facet.name: f"INSERT OR IGNORE INTO {_quote_identifier(_array_table_name(facet.name))} "
                "(document_id, value) VALUES (?, ?)"
                for facet in config.array_facets
            }

            connection.execute("BEGIN")
            for index, candidate in enumerate(candidates, start=1):
                document = _extract_document(index, candidate, config, warnings)
                if smoke_token is None:
                    smoke_token = _first_search_token(f"{document.title} {document.body}")
                if smoke_filter is None:
                    smoke_filter = _first_filter(document)
                _insert_document(connection, insert_sql, array_insert_sql, config, document)
                if index % BATCH_SIZE == 0:
                    connection.commit()
                    connection.execute("BEGIN")
            connection.commit()
            _finalize_database(connection, compact_db_path)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

        db_sha256 = _sha256_file(compact_db_path)
        db_file = f"search.{db_sha256}.db"
        db_path = config.output_dir / db_file
        compact_db_path.replace(db_path)

        _run_smoke_queries(db_path, smoke_token, smoke_filter)

        manifest = {
            "manifest_version": MANIFEST_VERSION,
            "db_schema_version": DB_SCHEMA_VERSION,
            "db_file": db_file,
            "db_sha256": db_sha256,
            "db_bytes": db_path.stat().st_size,
            "sqlite_page_size": SQLITE_PAGE_SIZE,
            "range_required": True,
            "range_block_bytes": RANGE_BLOCK_BYTES,
            "page_count": len(candidates),
            "config_hash": config.config_hash,
            "runtime_min_version": __version__,
        }
        manifest_path = config.output_dir / "search-manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        return CompileResult(
            db_path=db_path,
            manifest_path=manifest_path,
            manifest=manifest,
            page_count=len(candidates),
            warnings=tuple(warnings),
            skipped=skipped,
        )
    except BuildError:
        raise
    except Exception as error:
        raise BuildError("DATABASE_BUILD_FAILED", str(error)) from error
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _load_selectors(raw: dict[str, Any]) -> dict[str, str]:
    value = raw.get("selectors", {})
    if not isinstance(value, dict):
        raise BuildError("CONFIG_INVALID", "selectors must be an object")
    unknown = sorted(set(value) - SELECTOR_KEYS)
    if unknown:
        raise BuildError("CONFIG_INVALID", f"unknown selector key(s): {', '.join(unknown)}")

    selectors = {
        "title": "title, h1",
        "body": "body",
        "description": "meta[name='description']@content",
    }
    for key, selector in value.items():
        if not isinstance(selector, str) or not selector.strip():
            raise BuildError("CONFIG_INVALID", f"selector {key!r} must be a non-empty string")
        selectors[key] = selector.strip()
    for key, selector in selectors.items():
        _validate_selector_source(selector, f"selectors.{key}", allow_direct_attribute=False)
    return selectors


def _load_facets(raw: dict[str, Any]) -> tuple[FacetConfig, ...]:
    value = raw.get("facets", {})
    if not isinstance(value, dict):
        raise BuildError("CONFIG_INVALID", "facets must be an object")

    facets: list[FacetConfig] = []
    for name in sorted(value):
        if not IDENTIFIER_RE.match(name):
            raise BuildError("CONFIG_INVALID", f"facet name must match {IDENTIFIER_RE.pattern}: {name!r}")
        facet_raw = value[name]
        if not isinstance(facet_raw, dict):
            raise BuildError("CONFIG_INVALID", f"facet {name!r} must be an object")
        unknown = sorted(set(facet_raw) - FACET_KEYS)
        if unknown:
            raise BuildError("CONFIG_INVALID", f"unknown key(s) on facet {name!r}: {', '.join(unknown)}")
        facet_type = facet_raw.get("type")
        if facet_type not in FACET_TYPES:
            raise BuildError("CONFIG_INVALID", f"facet {name!r} has unsupported type: {facet_type!r}")
        source = facet_raw.get("source")
        if not isinstance(source, str) or not source.strip():
            raise BuildError("CONFIG_INVALID", f"facet {name!r} source must be a non-empty string")
        required = facet_raw.get("required", False)
        if not isinstance(required, bool):
            raise BuildError("CONFIG_INVALID", f"facet {name!r} required must be a boolean")
        _validate_selector_source(source.strip(), f"facets.{name}.source", allow_direct_attribute=True)
        facets.append(FacetConfig(name=name, type=facet_type, source=source.strip(), required=required))
    return tuple(facets)


def _load_composite_indices(raw: dict[str, Any], facets: dict[str, FacetConfig]) -> list[tuple[str, ...]]:
    value = raw.get("composite_indices", [])
    if not isinstance(value, list):
        raise BuildError("CONFIG_INVALID", "composite_indices must be an array")
    indices: list[tuple[str, ...]] = []
    for index_number, index in enumerate(value, start=1):
        if not isinstance(index, list) or len(index) < 2 or not all(isinstance(name, str) for name in index):
            raise BuildError("CONFIG_INVALID", f"composite_indices[{index_number}] must contain at least two facet names")
        for name in index:
            facet = facets.get(name)
            if facet is None:
                raise BuildError("CONFIG_INVALID", f"composite index references unknown facet: {name!r}")
            if facet.is_array:
                raise BuildError("CONFIG_INVALID", f"composite index cannot include array facet: {name!r}")
        indices.append(tuple(index))
    return indices


def _load_client(raw: dict[str, Any]) -> dict[str, str]:
    value = raw.get("client", {})
    if not isinstance(value, dict):
        raise BuildError("CONFIG_INVALID", "client must be an object")
    unknown = sorted(set(value) - CLIENT_KEYS)
    if unknown:
        raise BuildError("CONFIG_INVALID", f"unknown client key(s): {', '.join(unknown)}")
    client: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(item, str) or not item.strip():
            raise BuildError("CONFIG_INVALID", f"client.{key} must be a non-empty string")
        client[key] = item
    return client


def _validate_result_fields(result_fields: tuple[str, ...], facets: dict[str, FacetConfig]) -> None:
    allowed = {"id", "title", "url", "description"} | set(facets)
    for field_name in result_fields:
        if field_name not in allowed:
            raise BuildError("CONFIG_INVALID", f"result_fields references unknown field: {field_name!r}")


def _configure_build_database(connection: sqlite3.Connection) -> None:
    connection.execute(f"PRAGMA page_size = {SQLITE_PAGE_SIZE}")
    connection.execute("PRAGMA journal_mode = OFF")
    connection.execute("PRAGMA synchronous = OFF")
    connection.execute("PRAGMA temp_store = MEMORY")
    connection.execute("PRAGMA foreign_keys = OFF")
    connection.execute(f"PRAGMA user_version = {DB_SCHEMA_VERSION}")


def _create_schema(connection: sqlite3.Connection, config: DredgeConfig) -> None:
    scalar_columns = [f"{_quote_identifier(facet.name)} {SCALAR_SQL_TYPES[facet.type]}" for facet in config.scalar_facets]
    document_columns = [
        "id INTEGER PRIMARY KEY",
        "url TEXT NOT NULL UNIQUE",
        "title TEXT NOT NULL",
        "description TEXT",
        "content_hash TEXT NOT NULL",
        *scalar_columns,
    ]
    connection.execute(f"CREATE TABLE documents ({', '.join(document_columns)}) STRICT")
    connection.execute(
        "CREATE VIRTUAL TABLE documents_fts USING fts5("
        "title, body, content='', tokenize='unicode61 remove_diacritics 2')"
    )

    for facet in config.array_facets:
        table_name = _quote_identifier(_array_table_name(facet.name))
        connection.execute(
            f"CREATE TABLE {table_name} ("
            "document_id INTEGER NOT NULL, "
            "value TEXT NOT NULL, "
            "PRIMARY KEY (document_id, value)"
            ") WITHOUT ROWID"
        )
        connection.execute(
            f"CREATE INDEX {_quote_identifier(f'facet_{facet.name}_value_document_idx')} "
            f"ON {table_name}(value, document_id)"
        )

    for facet in config.scalar_facets:
        connection.execute(
            f"CREATE INDEX {_quote_identifier(f'documents_{facet.name}_idx')} "
            f"ON documents({_quote_identifier(facet.name)}, id)"
        )

    for index in config.composite_indices:
        name = "documents_" + "_".join(index) + "_idx"
        columns = ", ".join(_quote_identifier(column) for column in index)
        connection.execute(f"CREATE INDEX {_quote_identifier(name)} ON documents({columns}, id)")


def _document_insert_sql(config: DredgeConfig) -> str:
    columns = ["id", "url", "title", "description", "content_hash"] + [facet.name for facet in config.scalar_facets]
    placeholders = ", ".join("?" for _ in columns)
    sql_columns = ", ".join(_quote_identifier(column) for column in columns)
    return f"INSERT INTO documents ({sql_columns}) VALUES ({placeholders})"


def _insert_document(
    connection: sqlite3.Connection,
    insert_sql: str,
    array_insert_sql: dict[str, str],
    config: DredgeConfig,
    document: ExtractedDocument,
) -> None:
    values = [document.id, document.url, document.title, document.description, document.content_hash]
    values.extend(document.scalar_facets.get(facet.name) for facet in config.scalar_facets)
    connection.execute(insert_sql, values)
    connection.execute(
        "INSERT INTO documents_fts(rowid, title, body) VALUES (?, ?, ?)",
        (document.id, document.title, document.body),
    )
    for facet in config.array_facets:
        for value in document.array_facets.get(facet.name, ()):
            connection.execute(array_insert_sql[facet.name], (document.id, value))


def _extract_document(
    document_id: int,
    candidate: FileCandidate,
    config: DredgeConfig,
    warnings: list[BuildWarning],
) -> ExtractedDocument:
    try:
        html_bytes = candidate.path.read_bytes()
    except OSError as error:
        raise BuildError("HTML_READ_FAILED", f"failed to read {candidate.path}: {error}") from error

    soup = BeautifulSoup(html_bytes, "html.parser")
    _remove_non_indexable_content(soup)

    title_values = _extract_values(soup, config.selectors["title"])
    if title_values:
        title = title_values[0]
    else:
        title = candidate.url
        warnings.append(
            BuildWarning(
                code="SELECTOR_MISS",
                message=f"title selector matched no text in {candidate.path}; using URL as title",
                path=candidate.path,
                field="title",
                selector=config.selectors["title"],
            )
        )

    description_values = _extract_values(soup, config.selectors["description"])
    description = description_values[0] if description_values else None
    if not description_values:
        warnings.append(
            BuildWarning(
                code="SELECTOR_MISS",
                message=f"description selector matched no text in {candidate.path}",
                path=candidate.path,
                field="description",
                selector=config.selectors["description"],
            )
        )

    body_values = _extract_values(soup, config.selectors["body"])
    body = _normalize_text(" ".join(body_values))
    if not body:
        warnings.append(
            BuildWarning(
                code="SELECTOR_MISS",
                message=f"body selector matched no text in {candidate.path}",
                path=candidate.path,
                field="body",
                selector=config.selectors["body"],
            )
        )

    scalar_facets: dict[str, str | int | float | None] = {}
    array_facets: dict[str, tuple[str, ...]] = {}
    for facet in config.facets:
        raw_values = _extract_values(soup, facet.source)
        if facet.is_array:
            values = _normalize_array_values(raw_values)
            if facet.required and not values:
                raise BuildError(
                    "FACET_REQUIRED_MISSING",
                    f"missing required facet {facet.name!r} in {candidate.path} from source {facet.source!r}",
                )
            array_facets[facet.name] = tuple(values)
            continue

        if not raw_values:
            if facet.required:
                raise BuildError(
                    "FACET_REQUIRED_MISSING",
                    f"missing required facet {facet.name!r} in {candidate.path} from source {facet.source!r}",
                )
            scalar_facets[facet.name] = None
            continue

        if len(raw_values) > 1:
            warnings.append(
                BuildWarning(
                    code="FACET_MULTIPLE_VALUES",
                    message=f"facet {facet.name!r} found multiple values in {candidate.path}; using the first value",
                    path=candidate.path,
                    field=facet.name,
                    selector=facet.source,
                )
            )
        scalar_facets[facet.name] = _coerce_scalar_facet(facet, raw_values[0], candidate.path)

    return ExtractedDocument(
        id=document_id,
        url=candidate.url,
        title=title,
        description=description,
        body=body,
        content_hash=_sha256_bytes(html_bytes),
        scalar_facets=scalar_facets,
        array_facets=array_facets,
    )


def _remove_non_indexable_content(soup: BeautifulSoup) -> None:
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()
    for tag in soup.select("[hidden], [aria-hidden='true']"):
        tag.decompose()
    for tag in soup.select("[style]"):
        style = str(tag.get("style", "")).replace(" ", "").lower()
        if "display:none" in style or "visibility:hidden" in style:
            tag.decompose()


def _extract_values(soup: BeautifulSoup, source: str) -> list[str]:
    kind, selector, attribute = _parse_source(source, allow_direct_attribute=True)
    values: list[str] = []
    if kind == "attribute":
        for tag in soup.find_all(attrs={attribute: True}):
            values.extend(_normalize_attribute_value(tag.get(attribute)))
    elif kind == "selector_attribute":
        for tag in soup.select(selector):
            if tag.has_attr(attribute):
                values.extend(_normalize_attribute_value(tag.get(attribute)))
    else:
        for tag in soup.select(selector):
            values.append(tag.get_text(" ", strip=True))
    return [value for value in (_normalize_text(value) for value in values) if value]


def _normalize_attribute_value(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _normalize_array_values(values: list[str]) -> list[str]:
    normalized: set[str] = set()
    for value in values:
        for item in value.split(","):
            text = _normalize_text(item)
            if text:
                normalized.add(text)
    return sorted(normalized)


def _coerce_scalar_facet(facet: FacetConfig, value: str, path: Path) -> str | int | float:
    text = _normalize_text(value)
    if facet.type == "string":
        return text
    if facet.type == "integer":
        try:
            if not re.fullmatch(r"[-+]?\d+", text):
                raise ValueError
            return int(text, 10)
        except ValueError as error:
            raise BuildError("FACET_VALUE_INVALID", f"invalid integer value for facet {facet.name!r} in {path}: {value!r}") from error
    if facet.type == "number":
        try:
            return float(text)
        except ValueError as error:
            raise BuildError("FACET_VALUE_INVALID", f"invalid number value for facet {facet.name!r} in {path}: {value!r}") from error
    if facet.type == "boolean":
        lowered = text.lower()
        if lowered in {"true", "1", "yes", "y", "on"}:
            return 1
        if lowered in {"false", "0", "no", "n", "off"}:
            return 0
        raise BuildError("FACET_VALUE_INVALID", f"invalid boolean value for facet {facet.name!r} in {path}: {value!r}")
    if facet.type == "date":
        try:
            return date.fromisoformat(text).isoformat()
        except ValueError as error:
            raise BuildError("FACET_VALUE_INVALID", f"invalid ISO date value for facet {facet.name!r} in {path}: {value!r}") from error
    raise BuildError("CONFIG_INVALID", f"unsupported scalar facet type: {facet.type}")


def _finalize_database(connection: sqlite3.Connection, compact_db_path: Path) -> None:
    connection.execute("INSERT INTO documents_fts(documents_fts) VALUES('optimize')")
    connection.execute("ANALYZE")
    connection.execute("PRAGMA optimize")
    connection.commit()
    if compact_db_path.exists():
        compact_db_path.unlink()
    connection.execute(f"VACUUM INTO {_quote_sql_string(str(compact_db_path))}")


def _run_smoke_queries(
    db_path: Path,
    smoke_token: str | None,
    smoke_filter: tuple[str, str, str | int | float] | None,
) -> None:
    if smoke_token is None:
        raise BuildError("SMOKE_QUERY_FAILED", "could not find a token for the FTS smoke query")

    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        fts_count = connection.execute(
            "SELECT COUNT(*) FROM documents_fts WHERE documents_fts MATCH ?",
            (smoke_token,),
        ).fetchone()[0]
        if fts_count < 1:
            raise BuildError("SMOKE_QUERY_FAILED", f"FTS smoke query returned no rows for token {smoke_token!r}")

        if smoke_filter is None:
            filtered_count = connection.execute("SELECT COUNT(*) FROM documents WHERE id = 1").fetchone()[0]
        elif smoke_filter[0] == "array":
            _, name, value = smoke_filter
            filtered_count = connection.execute(
                f"SELECT COUNT(*) FROM {_quote_identifier(_array_table_name(name))} WHERE value = ?",
                (value,),
            ).fetchone()[0]
        else:
            _, name, value = smoke_filter
            filtered_count = connection.execute(
                f"SELECT COUNT(*) FROM documents WHERE {_quote_identifier(name)} = ?",
                (value,),
            ).fetchone()[0]
        if filtered_count < 1:
            raise BuildError("SMOKE_QUERY_FAILED", "filtered smoke query returned no rows")
    finally:
        connection.close()


def _first_search_token(text: str) -> str | None:
    for match in TOKEN_RE.finditer(text):
        token = match.group(0)
        if len(token) > 1:
            return token
    return None


def _first_filter(document: ExtractedDocument) -> tuple[str, str, str | int | float] | None:
    for name, value in document.scalar_facets.items():
        if value is not None:
            return ("scalar", name, value)
    for name, values in document.array_facets.items():
        if values:
            return ("array", name, values[0])
    return None


def _parse_source(source: str, allow_direct_attribute: bool) -> tuple[str, str, str]:
    if "@" in source:
        selector, attribute = source.rsplit("@", 1)
        return "selector_attribute", selector.strip(), attribute.strip()
    if allow_direct_attribute and source.startswith("data-"):
        return "attribute", "", source
    return "selector_text", source, ""


def _validate_selector_source(source: str, field_name: str, allow_direct_attribute: bool) -> None:
    kind, selector, attribute = _parse_source(source, allow_direct_attribute=allow_direct_attribute)
    if kind == "attribute":
        if not ATTRIBUTE_RE.match(attribute):
            raise BuildError("CONFIG_INVALID", f"{field_name} has invalid attribute source: {source!r}")
        return
    if kind == "selector_attribute" and not ATTRIBUTE_RE.match(attribute):
        raise BuildError("CONFIG_INVALID", f"{field_name} has invalid attribute name: {attribute!r}")
    if not selector:
        raise BuildError("CONFIG_INVALID", f"{field_name} has an empty CSS selector")
    try:
        BeautifulSoup("", "html.parser").select(selector)
    except Exception as error:
        raise BuildError("CONFIG_INVALID", f"{field_name} has invalid CSS selector {selector!r}: {error}") from error


def _required_path(raw: dict[str, Any], key: str, base_dir: Path) -> Path:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise BuildError("CONFIG_INVALID", f"{key} must be a non-empty string")
    return _resolve_path(value, base_dir)


def _resolve_path(value: str, base_dir: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def _absolute_path(path: Path) -> Path:
    path = path.expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def _optional_string(raw: dict[str, Any], key: str, default: str) -> str:
    value = raw.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise BuildError("CONFIG_INVALID", f"{key} must be a non-empty string")
    return value.strip()


def _optional_bool(raw: dict[str, Any], key: str, default: bool) -> bool:
    value = raw.get(key, default)
    if not isinstance(value, bool):
        raise BuildError("CONFIG_INVALID", f"{key} must be a boolean")
    return value


def _optional_string_list(raw: dict[str, Any], key: str, default: list[str]) -> list[str]:
    value = raw.get(key, default)
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise BuildError("CONFIG_INVALID", f"{key} must be an array of non-empty strings")
    return [item.strip() for item in value]


def _same_or_child(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _matches_any(rel_path: str, patterns: tuple[str, ...]) -> bool:
    pure_path = PurePosixPath(rel_path)
    for pattern in patterns:
        if pure_path.match(pattern) or fnmatch.fnmatchcase(rel_path, pattern):
            return True
        if pattern.startswith("**/"):
            root_pattern = pattern[3:]
            if pure_path.match(root_pattern) or fnmatch.fnmatchcase(rel_path, root_pattern):
                return True
    return False


def _canonical_url(base_url: str, rel_path: str) -> str:
    if rel_path == "index.html":
        url_path = ""
    elif rel_path.endswith("/index.html"):
        url_path = rel_path[: -len("index.html")]
    else:
        url_path = rel_path
    base = base_url if base_url.endswith("/") else f"{base_url}/"
    return urljoin(base, url_path)


def _normalize_text(value: str) -> str:
    return unicodedata.normalize("NFC", " ".join(value.split()))


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _array_table_name(facet_name: str) -> str:
    return f"facet_{facet_name}"


def _quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _quote_sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"
