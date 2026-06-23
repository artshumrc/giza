import type { Exec } from "./db";

export interface DredgeRange<T> {
  min?: T;
  max?: T;
}

export type DredgeFilterValue =
  | string
  | number
  | boolean
  | Array<string | number | boolean>
  | DredgeRange<number | string>;

export interface DredgeFilters {
  [facet: string]: DredgeFilterValue | undefined;
}

export interface DredgeSort {
  // A selectable `documents` column to order by (e.g. "title"). Unknown
  // columns are ignored and the default ordering is used instead.
  field: string;
  direction?: "asc" | "desc";
}

export interface DredgeSearchRequest {
  query?: string;
  filters?: DredgeFilters;
  limit?: number;
  offset?: number;
  includeFacets?: boolean | string[];
  // Explicit ordering. When omitted, results are ordered by relevance
  // (bm25) for keyword queries, or by document id for match-all browse.
  sort?: DredgeSort;
}

export interface DredgeFacetBucket {
  value: string | number | boolean;
  count: number;
}

export interface DredgeHit {
  [field: string]: string | number | boolean | null;
}

export interface DredgeSearchResponse {
  total: number;
  hits: DredgeHit[];
  facets?: Record<string, DredgeFacetBucket[]>;
  elapsedMs: number;
}

// Columns of the `documents` table that are not configurable scalar facets.
const RESERVED_COLUMNS = new Set(["id", "url", "title", "description", "content_hash"]);

export interface SchemaInfo {
  // Scalar facet columns living directly on the documents table.
  scalarColumns: string[];
  // Array facet name -> join table name (facet_<name>).
  arrayFacets: Map<string, string>;
  // All selectable document columns (excluding content_hash) in stable order.
  documentColumns: string[];
}

function quoteIdentifier(name: string): string {
  return `"${name.replace(/"/g, '""')}"`;
}

export function introspectSchema(exec: Exec): SchemaInfo {
  const tableInfo = exec("PRAGMA table_info(documents)");
  // PRAGMA table_info columns: cid, name, type, notnull, dflt_value, pk
  const allColumns = tableInfo.map((row) => String(row[1]));
  const scalarColumns = allColumns.filter((name) => !RESERVED_COLUMNS.has(name));
  const documentColumns = allColumns.filter((name) => name !== "content_hash");

  const arrayFacets = new Map<string, string>();
  const tables = exec(
    "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 'facet_%'",
  );
  for (const row of tables) {
    const table = String(row[0]);
    arrayFacets.set(table.slice("facet_".length), table);
  }

  return { scalarColumns, arrayFacets, documentColumns };
}

// Build a forgiving FTS5 MATCH expression from free-text user input. Terms are
// sanitized into quoted prefix searches, with compact/spaced identifier variants
// grouped together so `G7510`, `G 7510`, and `A644_NS` can find the same record.
interface QueryToken {
  text: string;
  subterms: string[];
}

interface QueryTerm {
  subterms: string[];
  identifier: boolean;
}

const TOKEN_RE = /[\p{L}\p{N}]+/gu;
const TOKEN_PART_RE = /[\p{L}]+|\p{N}+/gu;

export function buildMatchExpression(query: string): string | null {
  const terms = queryTerms(query.normalize("NFC"));
  if (terms.length === 0) {
    return null;
  }
  return terms.map(ftsTermExpression).join(" AND ");
}

function queryTokens(query: string): QueryToken[] {
  const tokens: QueryToken[] = [];
  for (const chunk of query.split(/\s+/)) {
    const subterms = chunk.match(TOKEN_RE) ?? [];
    if (subterms.length > 0) {
      tokens.push({ text: chunk, subterms });
    }
  }
  return tokens;
}

function queryTerms(query: string): QueryTerm[] {
  const tokens = queryTokens(query);
  const terms: QueryTerm[] = [];
  let index = 0;
  while (index < tokens.length) {
    const token = tokens[index];
    if (isIdentifierToken(token)) {
      terms.push({ subterms: token.subterms, identifier: true });
      index += 1;
      continue;
    }

    if (canStartSpacedIdentifier(token)) {
      const subterms = [...token.subterms];
      let nextIndex = index + 1;
      while (nextIndex < tokens.length && canContinueIdentifier(tokens[nextIndex])) {
        subterms.push(...tokens[nextIndex].subterms);
        nextIndex += 1;
      }
      if (nextIndex > index + 1 && hasLettersAndDigits(subterms)) {
        terms.push({ subterms, identifier: true });
        index = nextIndex;
        continue;
      }
    }

    for (const subterm of token.subterms) {
      terms.push({ subterms: [subterm], identifier: false });
    }
    index += 1;
  }
  return terms;
}

function isIdentifierToken(token: QueryToken): boolean {
  const compact = token.subterms.join("");
  return (
    compact.length > 0 &&
    hasLettersAndDigits(token.subterms) &&
    (/^(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9]+(?:[_-][A-Za-z0-9]+)*$/.test(token.text) ||
      token.subterms.length > 1 ||
      splitTokenParts(token.subterms).length > 1)
  );
}

function canStartSpacedIdentifier(token: QueryToken): boolean {
  if (token.subterms.length !== 1) {
    return false;
  }
  const subterm = token.subterms[0];
  if (!/[A-Za-z]/.test(subterm)) {
    return false;
  }
  return /\d/.test(subterm) || subterm.length <= 3 || subterm === subterm.toUpperCase();
}

function canContinueIdentifier(token: QueryToken): boolean {
  if (token.subterms.length !== 1) {
    return false;
  }
  const subterm = token.subterms[0];
  return (
    /^\d+$/.test(subterm) ||
    (/^[A-Za-z]+$/.test(subterm) &&
      (subterm.length <= 3 || subterm === subterm.toUpperCase())) ||
    (/^[A-Za-z0-9]+$/.test(subterm) && hasLettersAndDigits([subterm]))
  );
}

function hasLettersAndDigits(values: string[]): boolean {
  const text = values.join("");
  return /[A-Za-z]/.test(text) && /\d/.test(text);
}

function ftsTermExpression(term: QueryTerm): string {
  if (!term.identifier) {
    return ftsPrefixTerm(term.subterms[0]);
  }

  const expressions = [ftsPrefixTerm(term.subterms.join(""))];
  if (term.subterms.length > 1) {
    expressions.push(ftsPhrase(term.subterms));
  }
  const tokenParts = splitTokenParts(term.subterms);
  if (tokenParts.length > 1 && tokenParts.join("\0") !== term.subterms.join("\0")) {
    expressions.push(ftsPhrase(tokenParts));
  }

  const deduped = [...new Set(expressions)];
  if (deduped.length === 1) {
    return deduped[0];
  }
  return `(${deduped.join(" OR ")})`;
}

function splitTokenParts(subterms: string[]): string[] {
  return subterms.flatMap((subterm) => subterm.match(TOKEN_PART_RE) ?? []);
}

function ftsPhrase(subterms: string[]): string {
  return subterms.map(ftsPrefixTerm).join(" + ");
}

function ftsPrefixTerm(token: string): string {
  return `"${token.replace(/"/g, '""')}"*`;
}

interface WhereClause {
  sql: string[];
  bind: unknown[];
}

function isRange(value: unknown): value is DredgeRange<number | string> {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value) &&
    ("min" in value || "max" in value)
  );
}

function scalarFilterClause(column: string, value: DredgeFilterValue): WhereClause {
  const id = `d.${quoteIdentifier(column)}`;
  if (Array.isArray(value)) {
    if (value.length === 0) {
      return { sql: ["0"], bind: [] };
    }
    const placeholders = value.map(() => "?").join(", ");
    return { sql: [`${id} IN (${placeholders})`], bind: [...value] };
  }
  if (isRange(value)) {
    const sql: string[] = [];
    const bind: unknown[] = [];
    if (value.min !== undefined) {
      sql.push(`${id} >= ?`);
      bind.push(value.min);
    }
    if (value.max !== undefined) {
      sql.push(`${id} <= ?`);
      bind.push(value.max);
    }
    return { sql, bind };
  }
  return { sql: [`${id} = ?`], bind: [value] };
}

function arrayFilterClause(table: string, value: DredgeFilterValue): WhereClause {
  const values = Array.isArray(value) ? value : [value];
  if (values.length === 0) {
    return { sql: ["0"], bind: [] };
  }
  const placeholders = values.map(() => "?").join(", ");
  return {
    sql: [
      `EXISTS (SELECT 1 FROM ${quoteIdentifier(table)} ft ` +
        `WHERE ft.document_id = d.id AND ft.value IN (${placeholders}))`,
    ],
    bind: [...values],
  };
}

// Build the WHERE clauses + bind values for the given filters, optionally
// skipping one facet (used when computing that facet's own counts).
function buildFilterClauses(
  schema: SchemaInfo,
  filters: DredgeFilters,
  skipFacet?: string,
): WhereClause {
  const sql: string[] = [];
  const bind: unknown[] = [];
  for (const [name, value] of Object.entries(filters)) {
    if (value === undefined || value === null || name === skipFacet) {
      continue;
    }
    if (schema.scalarColumns.includes(name)) {
      const clause = scalarFilterClause(name, value);
      sql.push(...clause.sql);
      bind.push(...clause.bind);
    } else if (schema.arrayFacets.has(name)) {
      const clause = arrayFilterClause(schema.arrayFacets.get(name)!, value);
      sql.push(...clause.sql);
      bind.push(...clause.bind);
    }
    // Unknown filter keys are ignored.
  }
  return { sql, bind };
}

// Built-in free-text columns ordered case-insensitively so alphabetical sorts
// read naturally ("apple" before "Banana"). Other columns (ids, codes, facet
// values) keep their natural BINARY collation, which matches the indexes the
// compiler builds for them and lets those sorts use a covering index.
const NOCASE_SORT_COLUMNS = new Set(["title", "description"]);

// Build the ORDER BY clause. An explicit, valid sort wins; otherwise relevance
// (bm25) ordering is used for keyword queries and document id for match-all
// browse. `d.id` is always appended as a stable tiebreaker.
function buildOrderClause(
  schema: SchemaInfo,
  sort: DredgeSort | undefined,
  usesFts: boolean,
): string {
  if (sort && schema.documentColumns.includes(sort.field)) {
    const direction = sort.direction === "desc" ? "DESC" : "ASC";
    const collate = NOCASE_SORT_COLUMNS.has(sort.field) ? " COLLATE NOCASE" : "";
    return `ORDER BY d.${quoteIdentifier(sort.field)}${collate} ${direction}, d.id`;
  }
  return usesFts ? "ORDER BY bm25(documents_fts), d.id" : "ORDER BY d.id";
}

function facetNamesToCount(schema: SchemaInfo, includeFacets: boolean | string[]): string[] {
  if (includeFacets === true) {
    return [...schema.scalarColumns, ...schema.arrayFacets.keys()];
  }
  if (Array.isArray(includeFacets)) {
    return includeFacets.filter(
      (name) => schema.scalarColumns.includes(name) || schema.arrayFacets.has(name),
    );
  }
  return [];
}

export function search(
  exec: Exec,
  schema: SchemaInfo,
  request: DredgeSearchRequest,
): DredgeSearchResponse {
  const started = performance.now();
  const query = (request.query ?? "").trim();
  const matchExpr = query ? buildMatchExpression(query) : null;
  const filters = request.filters ?? {};
  const limit = Math.max(0, request.limit ?? 20);
  const offset = Math.max(0, request.offset ?? 0);

  // FROM + base WHERE shared by total/hits.
  const usesFts = matchExpr !== null;
  const from = usesFts
    ? "FROM documents_fts JOIN documents d ON d.id = documents_fts.rowid"
    : "FROM documents d";

  const baseWhere: string[] = [];
  const baseBind: unknown[] = [];
  if (usesFts) {
    baseWhere.push("documents_fts MATCH ?");
    baseBind.push(matchExpr);
  }
  const filterClause = buildFilterClauses(schema, filters);
  baseWhere.push(...filterClause.sql);
  baseBind.push(...filterClause.bind);

  const whereSql = baseWhere.length ? `WHERE ${baseWhere.join(" AND ")}` : "";

  // Total matching documents.
  const totalRows = exec(`SELECT COUNT(*) ${from} ${whereSql}`, baseBind);
  const total = Number(totalRows[0]?.[0] ?? 0);

  // Page of hits with all selectable document columns.
  const columns = schema.documentColumns;
  const select = columns.map((name) => `d.${quoteIdentifier(name)}`).join(", ");
  const order = buildOrderClause(schema, request.sort, usesFts);
  const hitRows = exec(
    `SELECT ${select} ${from} ${whereSql} ${order} LIMIT ? OFFSET ?`,
    [...baseBind, limit, offset],
  );
  const hits: DredgeHit[] = hitRows.map((row) => {
    const hit: DredgeHit = {};
    columns.forEach((name, index) => {
      hit[name] = row[index] as string | number | boolean | null;
    });
    return hit;
  });

  // Facet counts: each facet is counted applying all filters EXCEPT its own.
  let facets: Record<string, DredgeFacetBucket[]> | undefined;
  const facetNames = facetNamesToCount(schema, request.includeFacets ?? false);
  if (facetNames.length > 0) {
    facets = {};
    for (const name of facetNames) {
      const skipClause = buildFilterClauses(schema, filters, name);
      const where: string[] = [];
      const bind: unknown[] = [];
      if (usesFts) {
        where.push("documents_fts MATCH ?");
        bind.push(matchExpr);
      }
      where.push(...skipClause.sql);
      bind.push(...skipClause.bind);
      const facetWhere = where.length ? `WHERE ${where.join(" AND ")}` : "";

      if (schema.scalarColumns.includes(name)) {
        const col = `d.${quoteIdentifier(name)}`;
        const rows = exec(
          `SELECT ${col} AS value, COUNT(*) AS n ${from} ${facetWhere} ` +
            `GROUP BY ${col} ORDER BY n DESC`,
          bind,
        );
        facets[name] = rows
          .filter((row) => row[0] !== null)
          .map((row) => ({ value: row[0] as string | number | boolean, count: Number(row[1]) }));
      } else {
        const table = schema.arrayFacets.get(name)!;
        const rows = exec(
          `SELECT ft.value AS value, COUNT(*) AS n ` +
            `FROM ${quoteIdentifier(table)} ft ` +
            `JOIN documents d ON d.id = ft.document_id ` +
            (usesFts ? "JOIN documents_fts ON documents_fts.rowid = d.id " : "") +
            `${facetWhere} GROUP BY ft.value ORDER BY n DESC`,
          bind,
        );
        facets[name] = rows.map((row) => ({
          value: row[0] as string | number | boolean,
          count: Number(row[1]),
        }));
      }
    }
  }

  return { total, hits, facets, elapsedMs: performance.now() - started };
}
