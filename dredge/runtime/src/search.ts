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

export interface DredgeSearchRequest {
  query?: string;
  filters?: DredgeFilters;
  limit?: number;
  offset?: number;
  includeFacets?: boolean | string[];
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

// Build a forgiving FTS5 MATCH expression from free-text user input: each token
// is sanitized of FTS operator characters and turned into a prefix term, ANDed
// together. Returns null when the query has no usable tokens (match-all).
export function buildMatchExpression(query: string): string | null {
  const tokens = query
    .split(/\s+/)
    .map((token) => token.replace(/["*()^:\-]/g, "").trim())
    .filter((token) => token.length > 0);
  if (tokens.length === 0) {
    return null;
  }
  return tokens.map((token) => `${token}*`).join(" ");
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
  const order = usesFts ? "ORDER BY bm25(documents_fts), d.id" : "ORDER BY d.id";
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
