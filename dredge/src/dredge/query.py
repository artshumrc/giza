from __future__ import annotations

import re
import sqlite3
import time
import unicodedata
from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping

from .compiler import DredgeConfig, FacetConfig

DEFAULT_LIMIT = 20
ARRAY_RESULT_SEPARATOR = "\x1f"
TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
TOKEN_PART_RE = re.compile(r"[^\W_\d]+|\d+", re.UNICODE)
COMPACT_IDENTIFIER_RE = re.compile(
    r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9]+(?:[_-][A-Za-z0-9]+)*$"
)


@dataclass(frozen=True)
class _QueryToken:
    text: str
    subterms: tuple[str, ...]


@dataclass(frozen=True)
class _QueryTerm:
    subterms: tuple[str, ...]
    identifier: bool = False


class QueryError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class SearchRequest:
    query: str | None = None
    filters: Mapping[str, Any] | None = None
    limit: int = DEFAULT_LIMIT
    offset: int = 0
    include_facets: bool | str | tuple[str, ...] = False


@dataclass(frozen=True)
class BuiltSql:
    sql: str
    parameters: tuple[Any, ...]


@dataclass(frozen=True)
class BuiltSearchQueries:
    results: BuiltSql
    total: BuiltSql
    facets: dict[str, BuiltSql]


@dataclass(frozen=True)
class FacetBucket:
    value: str | int | float | bool
    count: int


@dataclass(frozen=True)
class SearchResponse:
    total: int
    hits: tuple[dict[str, Any], ...]
    facets: dict[str, tuple[FacetBucket, ...]] | None
    elapsed_ms: float


@dataclass(frozen=True)
class _Condition:
    sql: str
    parameters: tuple[Any, ...]


def escape_fts_query(query: str | None) -> str | None:
    if query is None:
        return None
    text = unicodedata.normalize("NFC", query)
    terms = _query_terms(text)
    if not terms:
        return None
    return " AND ".join(_fts_term_expression(term) for term in terms)


def _query_tokens(text: str) -> list[_QueryToken]:
    tokens: list[_QueryToken] = []
    for chunk in text.split():
        subterms = tuple(match.group(0) for match in TOKEN_RE.finditer(chunk))
        if subterms:
            tokens.append(_QueryToken(text=chunk, subterms=subterms))
    return tokens


def _query_terms(text: str) -> list[_QueryTerm]:
    tokens = _query_tokens(text)
    terms: list[_QueryTerm] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if _is_identifier_token(token):
            terms.append(_QueryTerm(token.subterms, identifier=True))
            index += 1
            continue

        if _can_start_spaced_identifier(token):
            subterms = list(token.subterms)
            next_index = index + 1
            while next_index < len(tokens) and _can_continue_identifier(
                tokens[next_index]
            ):
                subterms.extend(tokens[next_index].subterms)
                next_index += 1
            if next_index > index + 1 and _has_letters_and_digits(subterms):
                terms.append(_QueryTerm(tuple(subterms), identifier=True))
                index = next_index
                continue

        terms.extend(_QueryTerm((subterm,)) for subterm in token.subterms)
        index += 1
    return terms


def _is_identifier_token(token: _QueryToken) -> bool:
    compact = "".join(token.subterms)
    return bool(
        compact
        and _has_letters_and_digits(token.subterms)
        and (
            COMPACT_IDENTIFIER_RE.match(token.text)
            or len(token.subterms) > 1
            or len(_split_token_parts(token.subterms)) > 1
        )
    )


def _can_start_spaced_identifier(token: _QueryToken) -> bool:
    if len(token.subterms) != 1:
        return False
    subterm = token.subterms[0]
    has_letter = any(character.isalpha() for character in subterm)
    if not has_letter:
        return False
    return (
        any(character.isdigit() for character in subterm)
        or len(subterm) <= 3
        or subterm.isupper()
    )


def _can_continue_identifier(token: _QueryToken) -> bool:
    if len(token.subterms) != 1:
        return False
    subterm = token.subterms[0]
    return (
        subterm.isdigit()
        or (subterm.isalpha() and (len(subterm) <= 3 or subterm.isupper()))
        or (subterm.isalnum() and _has_letters_and_digits((subterm,)))
    )


def _has_letters_and_digits(subterms: tuple[str, ...] | list[str]) -> bool:
    text = "".join(subterms)
    return any(character.isalpha() for character in text) and any(
        character.isdigit() for character in text
    )


def _fts_term_expression(term: _QueryTerm) -> str:
    if not term.identifier:
        return _fts_prefix_term(term.subterms[0])

    expressions = [_fts_prefix_term("".join(term.subterms))]
    if len(term.subterms) > 1:
        expressions.append(_fts_phrase(term.subterms))
    token_parts = _split_token_parts(term.subterms)
    if len(token_parts) > 1 and token_parts != term.subterms:
        expressions.append(_fts_phrase(token_parts))

    deduped = list(dict.fromkeys(expressions))
    if len(deduped) == 1:
        return deduped[0]
    return "(" + " OR ".join(deduped) + ")"


def _split_token_parts(subterms: tuple[str, ...]) -> tuple[str, ...]:
    parts: list[str] = []
    for subterm in subterms:
        parts.extend(match.group(0) for match in TOKEN_PART_RE.finditer(subterm))
    return tuple(parts)


def _fts_phrase(subterms: tuple[str, ...]) -> str:
    return " + ".join(_fts_prefix_term(subterm) for subterm in subterms)


def _fts_prefix_term(token: str) -> str:
    return f'"{token.replace(chr(34), chr(34) + chr(34))}"*'


def build_search_queries(
    config: DredgeConfig,
    request: SearchRequest | Mapping[str, Any] | None = None,
) -> BuiltSearchQueries:
    normalized = _normalize_request(request)
    limit = _validate_limit(normalized.limit)
    offset = _validate_offset(normalized.offset)
    fts_query = escape_fts_query(normalized.query)
    conditions = _filter_conditions(config, normalized.filters or {})
    cte_sql, cte_parameters = _filtered_cte(fts_query, conditions)
    result_columns = ", ".join(_result_select_expressions(config))

    results_sql = (
        f"{cte_sql} "
        f"SELECT {result_columns}, filtered.rank AS score "
        "FROM filtered "
        "JOIN documents d ON d.id = filtered.id "
        "ORDER BY filtered.rank, d.id "
        "LIMIT ? OFFSET ?"
    )
    total_sql = f"{cte_sql} SELECT COUNT(*) FROM filtered"

    facet_queries = {
        name: BuiltSql(sql, cte_parameters)
        for name, sql in _facet_count_sql(config, cte_sql, _include_facet_names(config, normalized.include_facets)).items()
    }

    return BuiltSearchQueries(
        results=BuiltSql(results_sql, (*cte_parameters, limit, offset)),
        total=BuiltSql(total_sql, cte_parameters),
        facets=facet_queries,
    )


def search(
    connection: sqlite3.Connection,
    config: DredgeConfig,
    request: SearchRequest | Mapping[str, Any] | None = None,
) -> SearchResponse:
    started = time.perf_counter()
    queries = build_search_queries(config, request)
    total = int(connection.execute(queries.total.sql, queries.total.parameters).fetchone()[0])

    cursor = connection.execute(queries.results.sql, queries.results.parameters)
    columns = [description[0] for description in cursor.description]
    hits = tuple(_normalize_hit(config, dict(zip(columns, row, strict=True))) for row in cursor.fetchall())

    facets: dict[str, tuple[FacetBucket, ...]] | None = None
    if queries.facets:
        facet_map = config.facet_map
        facets = {}
        for name, built in queries.facets.items():
            facet = facet_map[name]
            facets[name] = tuple(
                FacetBucket(value=_normalize_output_value(facet, row[0]), count=int(row[1]))
                for row in connection.execute(built.sql, built.parameters)
            )

    elapsed_ms = (time.perf_counter() - started) * 1000
    return SearchResponse(total=total, hits=hits, facets=facets, elapsed_ms=elapsed_ms)


def _normalize_request(request: SearchRequest | Mapping[str, Any] | None) -> SearchRequest:
    if request is None:
        return SearchRequest()
    if isinstance(request, SearchRequest):
        return request
    if not isinstance(request, Mapping):
        raise QueryError("QUERY_INVALID", "search request must be a SearchRequest or mapping")

    allowed = {"query", "filters", "limit", "offset", "includeFacets", "include_facets"}
    unknown = sorted(set(request) - allowed)
    if unknown:
        raise QueryError("QUERY_INVALID", f"unknown search request key(s): {', '.join(str(key) for key in unknown)}")

    filters = request.get("filters")
    if filters is not None and not isinstance(filters, Mapping):
        raise QueryError("QUERY_INVALID", "filters must be an object")

    include_facets = request.get("include_facets", request.get("includeFacets", False))
    return SearchRequest(
        query=_optional_query(request.get("query")),
        filters=filters,
        limit=request.get("limit", DEFAULT_LIMIT),
        offset=request.get("offset", 0),
        include_facets=include_facets,
    )


def _optional_query(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise QueryError("QUERY_INVALID", "query must be a string")
    return value


def _validate_limit(value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise QueryError("QUERY_INVALID", "limit must be a positive integer")
    return value


def _validate_offset(value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise QueryError("QUERY_INVALID", "offset must be a non-negative integer")
    return value


def _filter_conditions(config: DredgeConfig, filters: Mapping[str, Any]) -> tuple[_Condition, ...]:
    facet_map = config.facet_map
    conditions: list[_Condition] = []
    for name in sorted(filters):
        facet = facet_map.get(name)
        if facet is None:
            raise QueryError("FILTER_INVALID", f"unknown filter facet: {name!r}")
        condition = _condition_for_facet(facet, filters[name])
        if condition is not None:
            conditions.append(condition)
    return tuple(conditions)


def _condition_for_facet(facet: FacetConfig, value: Any) -> _Condition | None:
    if value is None:
        return None
    if facet.is_array:
        values = _coerce_many(value, lambda item: _coerce_string(item, facet))
        if not values:
            return None
        table = _quote_identifier(_array_table_name(facet.name))
        placeholders = _placeholders(len(values))
        return _Condition(
            f"EXISTS (SELECT 1 FROM {table} af WHERE af.document_id = d.id AND af.value IN ({placeholders}))",
            tuple(values),
        )

    if facet.type in {"integer", "number", "date"} and isinstance(value, Mapping):
        return _range_condition(facet, value)

    values = _coerce_many(value, lambda item: _coerce_scalar_filter_value(facet, item))
    if not values:
        return None
    column = f"d.{_quote_identifier(facet.name)}"
    if len(values) == 1:
        return _Condition(f"{column} = ?", (values[0],))
    return _Condition(f"{column} IN ({_placeholders(len(values))})", tuple(values))


def _range_condition(facet: FacetConfig, value: Mapping[str, Any]) -> _Condition | None:
    unknown = sorted(set(value) - {"min", "max"})
    if unknown:
        raise QueryError("FILTER_INVALID", f"range filter for {facet.name!r} has unknown key(s): {', '.join(unknown)}")

    column = f"d.{_quote_identifier(facet.name)}"
    parts: list[str] = []
    parameters: list[Any] = []
    if value.get("min") is not None:
        parts.append(f"{column} >= ?")
        parameters.append(_coerce_scalar_filter_value(facet, value["min"]))
    if value.get("max") is not None:
        parts.append(f"{column} <= ?")
        parameters.append(_coerce_scalar_filter_value(facet, value["max"]))
    if not parts:
        return None
    return _Condition(" AND ".join(parts), tuple(parameters))


def _coerce_many(value: Any, coerce: Any) -> list[Any]:
    if isinstance(value, (list, tuple, set, frozenset)):
        raw_values = list(value)
    else:
        raw_values = [value]
    values: list[Any] = []
    for item in raw_values:
        if item is None:
            continue
        values.append(coerce(item))
    return values


def _coerce_scalar_filter_value(facet: FacetConfig, value: Any) -> str | int | float:
    if facet.type == "string":
        return _coerce_string(value, facet)
    if facet.type == "integer":
        return _coerce_integer(value, facet)
    if facet.type == "number":
        return _coerce_number(value, facet)
    if facet.type == "boolean":
        return _coerce_boolean(value, facet)
    if facet.type == "date":
        return _coerce_date(value, facet)
    raise QueryError("FILTER_INVALID", f"unsupported filter facet type: {facet.type}")


def _coerce_string(value: Any, facet: FacetConfig) -> str:
    if not isinstance(value, str):
        raise QueryError("FILTER_INVALID", f"filter {facet.name!r} expects a string value")
    text = unicodedata.normalize("NFC", " ".join(value.split()))
    if not text:
        raise QueryError("FILTER_INVALID", f"filter {facet.name!r} cannot be an empty string")
    return text


def _coerce_integer(value: Any, facet: FacetConfig) -> int:
    if isinstance(value, bool):
        raise QueryError("FILTER_INVALID", f"filter {facet.name!r} expects an integer value")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and re.fullmatch(r"[-+]?\d+", value.strip()):
        return int(value, 10)
    raise QueryError("FILTER_INVALID", f"filter {facet.name!r} expects an integer value")


def _coerce_number(value: Any, facet: FacetConfig) -> float:
    if isinstance(value, bool):
        raise QueryError("FILTER_INVALID", f"filter {facet.name!r} expects a number value")
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError as error:
            raise QueryError("FILTER_INVALID", f"filter {facet.name!r} expects a number value") from error
    raise QueryError("FILTER_INVALID", f"filter {facet.name!r} expects a number value")


def _coerce_boolean(value: Any, facet: FacetConfig) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int) and value in {0, 1}:
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y", "on"}:
            return 1
        if lowered in {"false", "0", "no", "n", "off"}:
            return 0
    raise QueryError("FILTER_INVALID", f"filter {facet.name!r} expects a boolean value")


def _coerce_date(value: Any, facet: FacetConfig) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError as error:
            raise QueryError("FILTER_INVALID", f"filter {facet.name!r} expects an ISO date value") from error
    raise QueryError("FILTER_INVALID", f"filter {facet.name!r} expects an ISO date value")


def _filtered_cte(fts_query: str | None, conditions: tuple[_Condition, ...]) -> tuple[str, tuple[Any, ...]]:
    where_sql = ""
    filter_parameters: list[Any] = []
    if conditions:
        where_sql = " WHERE " + " AND ".join(condition.sql for condition in conditions)
        for condition in conditions:
            filter_parameters.extend(condition.parameters)

    if fts_query is not None:
        return (
            "WITH matched AS ("
            "SELECT rowid AS id, bm25(documents_fts) AS rank "
            "FROM documents_fts "
            "WHERE documents_fts MATCH ?"
            "), filtered AS ("
            "SELECT d.id, matched.rank "
            "FROM matched "
            "JOIN documents d ON d.id = matched.id"
            f"{where_sql}"
            ")",
            (fts_query, *filter_parameters),
        )

    return (
        "WITH filtered AS ("
        "SELECT d.id, 0.0 AS rank "
        "FROM documents d"
        f"{where_sql}"
        ")",
        tuple(filter_parameters),
    )


def _result_select_expressions(config: DredgeConfig) -> tuple[str, ...]:
    fields = _unique(("id", *config.result_fields))
    facet_map = config.facet_map
    expressions: list[str] = []
    for field in fields:
        facet = facet_map.get(field)
        if facet is not None and facet.is_array:
            table_name = _quote_identifier(_array_table_name(facet.name))
            expressions.append(
                "(SELECT GROUP_CONCAT(value, char(31)) "
                f"FROM {table_name} af "
                "WHERE af.document_id = d.id) "
                f"AS {_quote_identifier(field)}"
            )
        else:
            expressions.append(f"d.{_quote_identifier(field)} AS {_quote_identifier(field)}")
    return tuple(expressions)


def _facet_count_sql(config: DredgeConfig, cte_sql: str, facet_names: tuple[str, ...]) -> dict[str, str]:
    facet_map = config.facet_map
    queries: dict[str, str] = {}
    for name in facet_names:
        facet = facet_map[name]
        if facet.is_array:
            table = _quote_identifier(_array_table_name(facet.name))
            queries[name] = (
                f"{cte_sql} "
                "SELECT af.value AS value, COUNT(*) AS count "
                "FROM filtered "
                f"JOIN {table} af ON af.document_id = filtered.id "
                "GROUP BY af.value "
                "ORDER BY count DESC, value ASC"
            )
        else:
            column = f"d.{_quote_identifier(facet.name)}"
            queries[name] = (
                f"{cte_sql} "
                f"SELECT {column} AS value, COUNT(*) AS count "
                "FROM filtered "
                "JOIN documents d ON d.id = filtered.id "
                f"WHERE {column} IS NOT NULL "
                f"GROUP BY {column} "
                "ORDER BY count DESC, value ASC"
            )
    return queries


def _include_facet_names(config: DredgeConfig, include_facets: bool | str | tuple[str, ...] | Any) -> tuple[str, ...]:
    if include_facets is False or include_facets is None:
        return ()
    if include_facets is True:
        return tuple(facet.name for facet in config.facets)
    if isinstance(include_facets, str):
        names = (include_facets,)
    elif isinstance(include_facets, (list, tuple, set, frozenset)):
        names = tuple(str(name) for name in include_facets)
    else:
        raise QueryError("QUERY_INVALID", "includeFacets must be a boolean or list of facet names")

    facet_map = config.facet_map
    unknown = [name for name in names if name not in facet_map]
    if unknown:
        raise QueryError("QUERY_INVALID", f"includeFacets references unknown facet(s): {', '.join(unknown)}")
    return _unique(names)


def _normalize_hit(config: DredgeConfig, hit: dict[str, Any]) -> dict[str, Any]:
    facet_map = config.facet_map
    for field, value in list(hit.items()):
        facet = facet_map.get(field)
        if facet is None:
            continue
        if facet.is_array:
            hit[field] = [] if value is None else str(value).split(ARRAY_RESULT_SEPARATOR)
        elif value is not None:
            hit[field] = _normalize_output_value(facet, value)
    if "score" in hit:
        hit["score"] = float(hit["score"])
    return hit


def _normalize_output_value(facet: FacetConfig, value: Any) -> str | int | float | bool:
    if facet.type == "boolean":
        return bool(value)
    return value


def _unique(values: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value not in seen:
            unique_values.append(value)
            seen.add(value)
    return tuple(unique_values)


def _placeholders(count: int) -> str:
    return ", ".join("?" for _ in range(count))


def _array_table_name(facet_name: str) -> str:
    return f"facet_{facet_name}"


def _quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'
