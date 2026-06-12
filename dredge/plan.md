# Dredge Production Implementation Plan

Status: Milestone 3 complete. The Python compiler now has a shared validation path, deterministic fixture coverage, typed facet normalization checks, structured build diagnostics, bounded warning aggregation, generated SQLite schema and facet indexes, finalized compact databases, read-only query-plan verification, a safe query builder, tested search and facet semantics, generated TypeScript client types, worker protocol types, and stale response handling. Runtime validation remains important, but it follows the hardened compiler artifact because the first useful artifact is the generated database.

Dredge is a compiled, configuration-driven, client-side search system for very large static sites. The target use case is a static site with 150,000+ generated pages, no permanent search server, and rich search plus faceted navigation in supported browsers.

The prior concept is directionally sound, but production readiness requires explicit contracts for configuration, generated assets, database schema, cache invalidation, browser support, query safety, performance budgets, and stress testing. This plan defines those contracts.

---

## 1. Goals

- Build a static SQLite search database from an already-built static site.
- Support 150,000+ HTML pages without keeping all page content in memory.
- Provide full-text search, typed filters, result pagination, and facet counts from the browser.
- Keep runtime search off the main thread by using a Web Worker.
- Ship the full SQLite database to the browser as a single Brotli-compressed asset and store the decompressed database in the browser's Origin Private File System.
- Require the most performant OPFS access path, synchronous access handles in a worker, and fail fast and loud when it is unavailable rather than silently degrading.
- Generate a type-safe client API from the exact search configuration.
- Produce deterministic, content-addressed assets that are safe to deploy on static hosting.

---

## 2. Non-Goals For The First Production Version

- No server-hosted search fallback.
- No support for browsers that cannot provide synchronous OPFS access handles in a worker.
- No runtime index building in the browser.
- No arbitrary SQL API exposed to application code.
- No silent downgrade to a smaller or less capable search mode.
- No crawler for dynamic, JavaScript-rendered content. Dredge consumes the final static HTML output.

Applications can provide their own fallback UI when Dredge reports an unsupported runtime or hosting configuration.

---

## 3. High-Level Architecture

```text
[Build Time]
static HTML output
  + dredge.config.json
        |
        v
  dredge validate
        |
        v
  dredge compile
        |
        +--> search/search-manifest.json
        +--> search/search.<db_hash>.db.br
        +--> search/dredge-worker.<hash>.js
        +--> generated dredge-client.ts

[Runtime]
application UI
        |
        v
generated DredgeSearchClient
        |
        v
Web Worker
        |
        +--> support check (sync OPFS access handles required)
        +--> manifest fetch
        +--> full compressed db download + brotli decompress
        +--> OPFS storage via sync access handles
        +--> read-only SQLite connection
        +--> parameterized search and facet queries
```

The main thread never opens SQLite and never performs database I/O. SQLite access, database download and decompression, and OPFS storage work are isolated inside the worker.

---

## 4. Initial Implementation Strategy

Build the compiler first in Python. The initial compiler should favor correctness, deterministic output, inspectable errors, and a usable SQLite artifact over maximum throughput.

Python compiler requirements:

- Use Python for the CLI, HTML crawler, extraction pipeline, SQLite population, and manifest generation.
- Use `uv` for Python commands, dependency management, and test execution.
- Use Python's `sqlite3` module initially if the bundled SQLite has FTS5 support; otherwise fail clearly and document the required SQLite build.
- Use a tolerant HTML parser library rather than regular expressions.
- Keep the compiler implementation simple until the first 150,000 page stress run identifies real bottlenecks.
- Accept basic batching and transactions from the start, but defer advanced parallel parsing, custom tokenization, and low-level SQLite tuning until after correctness is proven.
- Produce a database that can be opened and queried locally before any browser runtime work begins.

Implementation order for the first pass:

1. Load and validate `dredge.config.json`.
2. Discover HTML files deterministically.
3. Extract URL, title, description, body text, and configured facets.
4. Create the SQLite schema.
5. Insert documents, facet rows, and FTS rows.
6. Finalize the database and write `search-manifest.json`.
7. Run local smoke queries against the generated database.

Client-side build tooling:

- The Python compiler produces the database, manifest, and generated `dredge-client.ts`; it does not bundle JavaScript.
- Any build step required to produce the runtime worker bundle (`dredge-worker.<hash>.js`) and any WASM assets uses `pnpm` for package management and Vite for bundling.
- Use Vite to bundle the worker as an ES module worker, emit content-addressed filenames, and copy required SQLite WASM assets into `output_dir`.
- The generated `dredge-client.ts` is plain TypeScript that the consuming app compiles with its own toolchain; Dredge does not require the app to use Vite.
- Pin Node and `pnpm` versions, commit the `pnpm-lock.yaml`, and keep the worker build reproducible.

---

## 5. Production Configuration Contract

The configuration must be validated before any file crawling starts. Unknown keys should be rejected by default so typos do not silently change the generated schema.

Example:

```json
{
  "$schema": "https://dredge.dev/schema/v1.json",
  "source_dir": "./dist",
  "output_dir": "./public/search",
  "base_url": "/",
  "include": ["**/*.html"],
  "exclude": ["404.html", "admin/**"],
  "selectors": {
    "title": "title, h1",
    "body": "main",
    "description": "meta[name='description']@content"
  },
  "facets": {
    "category": {
      "type": "string",
      "source": "data-dredge-category",
      "required": true
    },
    "tags": {
      "type": "string_array",
      "source": "meta[property='article:tag']@content"
    },
    "year": {
      "type": "integer",
      "source": "data-dredge-year"
    }
  },
  "result_fields": ["title", "url", "description", "category", "year"],
  "composite_indices": [["category", "year"]],
  "client": {
    "out": "./src/dredge-client.ts",
    "worker_url": "/search/dredge-worker.js"
  }
}
```

Configuration rules:

- `source_dir` must exist and must be read-only from Dredge's perspective.
- `output_dir` must be separate from `source_dir` unless explicitly allowed, to avoid indexing generated search assets.
- `include` and `exclude` are evaluated deterministically and the final file list is sorted before processing.
- Facet names become generated SQL identifiers and TypeScript fields, so they must match `^[a-zA-Z_][a-zA-Z0-9_]*$`.
- Facet types are limited to `string`, `string_array`, `integer`, `number`, `boolean`, and `date` for the first production version.
- `string_array` facets are normalized into separate join tables rather than serialized into one text column.
- Missing required facets halt the build with the exact file path and facet name.
- Undeclared facet attributes in HTML halt the build in strict mode.
- Selector misses for optional fields emit warnings with counts and sample file paths.

---

## 6. Generated Asset Contract

Every compile produces these deployable assets:

| Asset | Purpose | Caching Strategy |
| --- | --- | --- |
| `search-manifest.json` | Current database identity, size, hashes, schema, and runtime compatibility. | Fetched with `cache: "no-cache"`. |
| `search.<db_hash>.db.br` | Immutable, Brotli-compressed SQLite database downloaded in full and decompressed in the worker. | Content-addressed filename. Safe for long-lived static caching. |
| `dredge-worker.<hash>.js` | Runtime worker bundle. | Content-addressed filename. |
| `dredge-client.ts` | Generated typed client used by the app. | Committed or generated during the app build. |

Manifest shape:

```json
{
  "manifest_version": 1,
  "db_schema_version": 1,
  "db_file": "search.4f3a1c....db.br",
  "db_sha256": "4f3a1c...",
  "db_bytes": 73400320,
  "db_compressed_bytes": 21544960,
  "db_compression": "brotli",
  "sqlite_page_size": 16384,
  "page_count": 150000,
  "config_hash": "9dd2...",
  "runtime_min_version": "0.1.0",
  "worker_file": "dredge-worker.1b7e....js"
}
```

Determinism requirements:

- The same inputs should produce the same database bytes in deterministic mode.
- File processing order must be stable.
- Document ids must be assigned from sorted canonical URLs.
- Build timestamps must not be stored in the database by default.
- The database filename must be derived from the final database hash.

Runtime access requirements:

- The full database is transferred once as a single Brotli-compressed asset and decompressed in the worker.
- The decompressed database is stored in OPFS and opened read-only through a synchronous-access-handle VFS.
- The OPFS storage namespace is derived from `db_sha256`, which identifies the decompressed, immutable database artifact.
- `db_sha256` is computed over the decompressed database bytes and may be verified after download because the whole database is local before the first query.
- `db_compressed_bytes` and `db_compression` describe the over-the-wire asset; `db_bytes` describes the decompressed database written to OPFS.

---

## 7. Build-Time Python Compiler

### 7.1 Validation Phase

`dredge validate` and the first phase of `dredge compile` must validate:

- JSON schema correctness.
- Source and output directory safety.
- Selector syntax.
- Facet names and type declarations.
- Composite index references.
- Client output path.
- Runtime asset base URL.

Validation must fail before creating output files when the configuration is invalid.

### 7.2 File Discovery

The compiler should discover files with bounded memory use:

- Walk `source_dir` using the configured include and exclude patterns.
- Ignore directories commonly generated by Dredge, including the configured `output_dir` if it sits under `source_dir`.
- Do not follow symlinks by default.
- Sort canonical URLs before assigning document ids.
- Record skipped files and the reason they were skipped.

### 7.3 HTML Extraction

Each HTML file is read once for extraction. The compiler should not retain full HTML or body text after inserting the relevant data into the build database.

Extraction rules:

- Parse HTML with a tolerant streaming or tokenizing parser, not regular expressions.
- Extract `url`, `title`, `description`, body text, and configured facets.
- Prefer configured selectors and metadata attributes over hard-coded assumptions.
- Strip `script`, `style`, `noscript`, template content, and hidden boilerplate where practical.
- Normalize whitespace and decode entities.
- Normalize Unicode to NFC.
- Enforce facet type conversion during extraction.
- Emit actionable errors with file path, selector, field, and invalid value.

### 7.4 SQLite Build Strategy

The compiler creates a temporary build database first, then writes the final compact database with `VACUUM INTO`.

Build pragmas for the temporary database:

```sql
PRAGMA page_size = 16384;
PRAGMA journal_mode = OFF;
PRAGMA synchronous = OFF;
PRAGMA temp_store = MEMORY;
PRAGMA foreign_keys = OFF;
```

These pragmas are acceptable only because the database is a disposable build artifact. If the build is interrupted, the compiler deletes the temporary artifact and starts over.

Ingestion rules:

- Use prepared statements for all inserts.
- Batch writes in explicit transactions.
- Start with 10,000 documents per transaction, then tune using the stress harness.
- Store page body text only in a temporary FTS staging table or insert it directly into the FTS table.
- Do not store full body text in the final `documents` table unless a future highlighting feature explicitly requires it.

### 7.5 Final Database Schema

The first production schema uses one primary document table, one contentless FTS5 table, and generated facet tables for array facets.

Representative schema:

```sql
CREATE TABLE documents (
  id INTEGER PRIMARY KEY,
  url TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  description TEXT,
  content_hash TEXT NOT NULL,
  category TEXT,
  year INTEGER
) STRICT;

CREATE VIRTUAL TABLE documents_fts USING fts5(
  title,
  body,
  content='',
  tokenize='unicode61 remove_diacritics 2'
);

CREATE TABLE facet_tags (
  document_id INTEGER NOT NULL,
  value TEXT NOT NULL,
  PRIMARY KEY (document_id, value)
) WITHOUT ROWID;

CREATE INDEX documents_category_year_idx ON documents(category, year, id);
CREATE INDEX documents_year_idx ON documents(year, id);
CREATE INDEX facet_tags_value_document_idx ON facet_tags(value, document_id);
```

Schema rules:

- `documents_fts.rowid` must equal `documents.id`.
- Scalar facets live on `documents` with typed columns.
- Array facets get one generated table per facet.
- Every filterable scalar facet gets an index unless the stress harness proves it is unnecessary.
- Composite indexes are generated exactly from configuration and validated against query plans.
- The final database is opened read-only at runtime.

FTS rules:

- Default query mode is simple user search, not raw FTS syntax.
- User input is tokenized and escaped before becoming the bound `MATCH` parameter.
- Advanced FTS syntax can be added later as an explicit opt-in API.
- Empty search queries skip the FTS table and filter directly against `documents`.
- Ranking uses `bm25(documents_fts)` plus a deterministic tie-breaker on `documents.id`.

Finalization sequence:

```sql
INSERT INTO documents_fts(documents_fts) VALUES('optimize');
ANALYZE;
PRAGMA optimize;
VACUUM INTO '<output_tmp_db>';
```

After finalization, the compiler computes SHA-256 over the final database, renames it to `search.<hash>.db`, writes the manifest, and removes temporary files.

---

## 8. Query Semantics

The runtime query engine must have explicit, testable semantics.

Search request shape:

```ts
export interface DredgeSearchRequest {
  query?: string;
  filters?: DredgeFilters;
  limit?: number;
  offset?: number;
  includeFacets?: boolean | Array<keyof DredgeFilters>;
}
```

Filter semantics:

- Different facets are combined with `AND`.
- Multiple selected values within the same scalar facet are combined with `OR`.
- Multiple selected values within an array facet match any selected value by default.
- Numeric and date facets support exact values and inclusive ranges.
- `null` facet values are not returned as facet buckets unless explicitly requested later.

Facet count semantics:

- Initial production behavior returns counts after all active filters are applied.
- Disjunctive self-facet counts are a future enhancement unless required by the first consuming UI.
- Counts must be deterministic and must match the same document universe as the result list.

SQL safety rules:

- Values are always passed as bound parameters.
- SQL identifiers are generated only from validated configuration keys.
- The query builder must not concatenate raw user input into SQL.
- The FTS query string is bound as a parameter after Dredge escaping and tokenization.
- SQL generation must be covered by snapshot tests for representative filters.

Representative query shape:

```sql
WITH matched AS (
  SELECT rowid AS id, bm25(documents_fts) AS rank
  FROM documents_fts
  WHERE documents_fts MATCH ?
), filtered AS (
  SELECT d.id, d.url, d.title, d.description, d.category, d.year, matched.rank
  FROM matched
  JOIN documents d ON d.id = matched.id
  WHERE d.category IN (?, ?)
    AND d.year BETWEEN ? AND ?
)
SELECT *
FROM filtered
ORDER BY rank, id
LIMIT ? OFFSET ?;
```

Array facet filters use `EXISTS` against the generated facet table.

---

## 9. Generated Client API

`dredge codegen` produces a typed wrapper based on `dredge.config.json`. `dredge compile` should run code generation by default unless disabled.

Generated types:

```ts
export interface DredgeFilters {
  category?: string | string[];
  tags?: string | string[];
  year?: number | number[] | { min?: number; max?: number };
}

export interface DredgeResult {
  id: number;
  title: string;
  url: string;
  description?: string;
  category?: string;
  year?: number;
  score: number;
}

export interface DredgeSearchResponse {
  total: number;
  hits: DredgeResult[];
  facets?: Record<string, Array<{ value: string | number | boolean; count: number }>>;
  elapsedMs: number;
}
```

Client behavior:

- Lazily start the worker on first use or explicit `init()`.
- Expose status changes for boot, manifest fetch, download, decompression, OPFS storage, ready, and failure states.
- Reject searches before readiness with a typed error.
- Assign sequence ids to search requests and discard stale responses from older keystrokes.
- Support debouncing at the application layer rather than hard-coding debounce in the client.
- Terminate the worker via `destroy()`.

---

## 10. Runtime Database Download, OPFS Storage, And SQLite Open

### 10.1 Support Detection

The worker must check browser support before downloading or opening the database. Support detection performs no database I/O.

Required support:

- `Worker` module support from the application.
- WebAssembly support required by the selected SQLite runtime.
- OPFS root access in the worker, verified by `navigator.storage.getDirectory`.
- Synchronous OPFS access handles in the worker, verified by `FileSystemFileHandle.prototype.createSyncAccessHandle`. This is the most performant OPFS storage path and is mandatory.
- A Brotli decompression path for the compressed database asset.

Synchronous OPFS access handles are a hard requirement. If `createSyncAccessHandle` is unavailable in the worker, the runtime returns `UNSUPPORTED_SYNC_ACCESS` immediately and does not attempt any slower OPFS access mode or any in-memory fallback. The failure is explicit and loud.

Unsupported cases return a typed error to the main thread. They do not throw unstructured errors and do not download the database.

### 10.2 Database Download, Decompression, And Storage Lifecycle

The runtime ships the entire database to the browser as a single Brotli-compressed asset, decompresses it, and stores the decompressed database in an OPFS file opened through a synchronous access handle. The OPFS copy is the persistent cache, so warm boots skip the network download and decompression entirely.

Boot sequence:

1. Fetch `search-manifest.json` with `cache: "no-cache"`.
2. Validate manifest version and runtime compatibility.
3. Run support detection, including the mandatory synchronous OPFS access handle check.
4. Derive the OPFS storage path from `db_sha256`.
5. If a complete OPFS database for the current `db_sha256` already exists, open it directly and skip download.
6. Otherwise fetch the full compressed database asset `search.<db_hash>.db.br`.
7. Decompress the asset to the raw database bytes.
8. Write the decompressed bytes to a temporary OPFS file via a synchronous access handle.
9. Verify the decompressed byte length against `db_bytes`, then atomically promote the temporary file to the final `db_sha256` path.
10. Open SQLite read-only against the OPFS file through the synchronous-access-handle VFS.
11. Remove obsolete database files from prior `db_sha256` namespaces after the current database is ready or when quota pressure requires eviction.

Storage rules:

- The OPFS storage namespace is derived from `db_sha256` so a new database never collides with a stale one.
- Decompressed bytes are written to a temporary file and become visible as the active database only after the full write succeeds and the byte length is verified.
- The runtime may verify `db_sha256` over the decompressed bytes; full verification is allowed here because the entire database is local before the first query.

Read-only open tuning:

- After opening, the runtime must set a page cache large enough to hold effectively the whole database (`PRAGMA cache_size = -131072`, i.e. 128 MB for the current ~90 MB corpus). This is mandatory, not optional: with the default ~8 MB cache, a broad ranked query repeatedly re-reads index pages through the OPFS synchronous-access-handle path and degrades from milliseconds to **tens of seconds**. Validation measured a broad-term ranked query exceeding 160 s with the default cache versus under 200 ms (p95) once the cache was sized to the database.
- `PRAGMA temp_store = MEMORY` keeps sorts and transient tables off the OPFS-backed file.
- `PRAGMA query_only = 1` enforces the read-only contract at the engine level.
- The first ranked query of a session pays a one-time cost (~1.6 s on the 150k corpus) to page in the FTS index and compute global statistics; subsequent warm queries are within budget. Optionally issue a background warmup query immediately after open.
- A no-persistent-storage mode is not supported. Synchronous OPFS storage is required.

Decompression rules:

- The compressed asset is transferred as `search.<db_hash>.db.br`.
- If the host serves the asset with `Content-Encoding: br`, the runtime fetches the transparently decompressed bytes directly.
- If the host serves the asset as an opaque body, the runtime decompresses Brotli in the worker before writing to OPFS.
- The chosen decompression path must produce bytes whose length matches `db_bytes`.

Failure recovery:

- A partial or interrupted OPFS write is discarded and the temporary file is deleted on the next boot.
- A decompressed byte length that does not match `db_bytes` returns `DB_SIZE_MISMATCH` and the temporary file is deleted.
- A failed or corrupt download returns `DB_DOWNLOAD_FAILED`.
- A Brotli decompression failure returns `DB_DECOMPRESS_FAILED`.
- A corrupt OPFS database is deleted and re-downloaded once before returning `DB_STORAGE_CORRUPT` or the underlying SQLite error.
- Storage quota errors evict obsolete database namespaces first. If the current database still cannot be stored, return `QUOTA_EXCEEDED` rather than silently switching modes.
- Lock contention retries with bounded backoff, then returns `SQLITE_BUSY_LOCKED`.

### 10.3 Multi-Tab Behavior

Use a maintained synchronous-access-handle OPFS SQLite VFS rather than writing a custom VFS first.

Production requirements:

- Two tabs from the same origin can initialize and query without corrupting the database.
- Concurrent first-boot downloads from two tabs must converge on a single stored database without corrupting the OPFS file. Use a coordinated write so only one tab promotes the final file.
- If the VFS cannot satisfy multi-tab read-only access reliably, Milestone 4 must stop runtime implementation and choose a different runtime strategy.

### 10.4 Worker State Machine

Runtime state should be explicit:

```text
idle
  -> checking_support
  -> fetching_manifest
  -> checking_storage
  -> downloading_db        (skipped when a valid OPFS copy exists)
  -> decompressing_db      (skipped when a valid OPFS copy exists)
  -> writing_opfs          (skipped when a valid OPFS copy exists)
  -> opening_db
  -> ready

Any state can transition to failed with a typed DredgeError.
```

Typed error codes:

| Code | Meaning |
| --- | --- |
| `UNSUPPORTED_OPFS` | OPFS directory access is missing. |
| `UNSUPPORTED_SYNC_ACCESS` | Synchronous OPFS access handles are unavailable in the worker. This is a hard, loud failure. |
| `MANIFEST_FETCH_FAILED` | Manifest could not be fetched or parsed. |
| `RUNTIME_VERSION_MISMATCH` | Manifest requires a newer runtime. |
| `DB_DOWNLOAD_FAILED` | The compressed database asset failed to download or returned invalid bytes. |
| `DB_DECOMPRESS_FAILED` | Brotli decompression of the database asset failed. |
| `DB_SIZE_MISMATCH` | The decompressed database byte length does not match the manifest. |
| `DB_STORAGE_CORRUPT` | The stored OPFS database could not be used after one eviction and re-download attempt. |
| `QUOTA_EXCEEDED` | OPFS writes fail after allowed eviction. |
| `SQLITE_OPEN_FAILED` | SQLite could not open the OPFS database. |
| `SQLITE_BUSY_LOCKED` | OPFS or SQLite locking did not resolve within the retry budget. |
| `QUERY_FAILED` | A prepared query failed unexpectedly. |

Diagnostics events are emitted locally to application code. No outbound telemetry is sent by default.

---

## 11. Performance Targets And Acceptance Budgets

Do not claim single-digit millisecond search until the stress harness proves it. Production targets should be realistic and measured on reference devices.

Initial acceptance targets for the 150,000 page stress dataset:

| Area | Target |
| --- | --- |
| Compiler memory | Peak RSS under 2 GB. |
| Compiler correctness | 100 percent of generated fixture pages are indexed or reported as skipped with reason. |
| Final DB size | Measured initially in Milestone 0 and stress-tested in Milestone 6. Initial soft target: under 150 MB uncompressed and under 50 MB Brotli-compressed over the wire. |
| Unsupported browser failure | Typed failure before downloading or opening the database when synchronous OPFS access handles are unavailable. |
| Cold boot behavior | First load transfers the manifest plus the single compressed database asset, then decompresses and stores it once in OPFS. |
| Warm startup | Ready under 1 second when a valid OPFS database already exists, with no database download or decompression on a current desktop browser. |
| Query latency | p95 under 150 ms for search plus active filters on reference desktop hardware. |
| Facet latency | p95 under 300 ms for requested facet counts on reference desktop hardware. |
| Typing behavior | Stale worker responses are discarded and never overwrite newer results. |
| Multi-tab | Two tabs can query concurrently for 5 minutes without corruption or untyped errors. |

Reference devices and browsers must be recorded in benchmark output. Targets can be tightened after real measurements.

---

## 12. Stress And Test Plan

### 12.1 Unit Tests

- Configuration validation.
- Selector parsing.
- Facet type coercion and normalization.
- URL canonicalization.
- FTS query escaping.
- SQL query generation.
- TypeScript code generation.
- Manifest validation.

### 12.2 Integration Tests

- Compile a small fixture site and compare known search results.
- Verify scalar and array facet filters.
- Verify facet counts with and without active filters.
- Verify empty query behavior.
- Verify deterministic database hashes for unchanged inputs.
- Verify schema migration rejection when runtime and manifest are incompatible.

### 12.3 Browser Tests

- First boot fetches the manifest, downloads the compressed database, decompresses it, stores it in OPFS, and opens it read-only.
- Warm boot reuses the OPFS database and performs no database download or decompression.
- Missing synchronous OPFS access handles fail with `UNSUPPORTED_SYNC_ACCESS` before downloading or opening the database.
- Private browsing or quota denial returns a typed error.
- A truncated or corrupt download fails with `DB_DOWNLOAD_FAILED` or `DB_SIZE_MISMATCH`.
- A corrupt OPFS database is deleted and re-downloaded once.
- Two tabs query simultaneously and converge on a single stored database.
- Worker termination and recreation do not corrupt the stored database.

### 12.4 Stress Harness

Build a synthetic site generator before optimizing the compiler.

Stress dataset requirements:

- 150,000+ HTML files.
- Realistic title and body lengths.
- High-cardinality and low-cardinality facets.
- Multi-value tags.
- Skewed distributions to expose bad query plans.
- Repeated common terms and rare terms.
- A known answer set for correctness assertions.

Stress output must include:

- Page count.
- Input bytes.
- Build duration.
- Peak memory.
- Final DB bytes.
- Manifest bytes.
- Runtime first-boot timing, including download, decompression, and OPFS write.
- Runtime warm-boot timing.
- Compressed transfer bytes and decompressed database bytes.
- Brotli compression ratio.
- Query p50, p95, and p99.
- Facet p50, p95, and p99.

---

## 13. Security, Privacy, And Hosting Requirements

Security requirements:

- Never execute scripts from indexed HTML.
- Never concatenate user values into SQL.
- Validate generated SQL identifiers from configuration.
- Treat the database as public static content. Do not put private data in indexed pages.
- Validate manifest JSON before using paths or hashes.
- Keep worker messages schema-validated.

Privacy requirements:

- No default analytics or outbound telemetry.
- Search queries stay local. The network sees only static asset requests for the manifest, worker, WASM, and the compressed database file.
- Diagnostics are exposed to the host app so the app can decide what to log.

Hosting requirements:

- Search assets should be served from the same origin as the app unless CORS is explicitly configured.
- The database asset is downloaded in full as a single Brotli-compressed file, so HTTP Range support is not required.
- If the host sets `Content-Encoding: br`, it must serve the exact compressed artifact and the runtime relies on transparent decompression; otherwise the runtime decompresses the opaque body itself.
- The host must not double-compress or otherwise re-transform the `.db.br` asset in a way that changes the bytes the runtime expects.
- If search assets are cross-origin, CORS must allow the asset requests and expose `Content-Length` and any cache validators used by the runtime.
- The manifest should not rely on custom cache headers because some static hosts provide limited header control.
- Hashed filenames are required for database and worker assets.
- The worker and WASM assets must be compatible with the site's Content Security Policy.
- Documentation must list required CSP directives for worker and WebAssembly loading.

---

## 14. Implementation Milestones

### Milestone 0: Python Compiler MVP

Status: complete.

Purpose: produce the first useful Dredge artifact: a SQLite database built from static HTML files. This milestone intentionally prioritizes correctness and debuggability over compiler speed.

Deliverables:

- Python CLI entry point for `dredge compile`.
- Minimal `dredge validate` path shared by `compile`.
- FTS5 capability check for the active Python SQLite build.
- Deterministic HTML file discovery from `source_dir`, `include`, and `exclude`.
- Tolerant HTML extraction for URL, title, description, body text, and configured facets.
- Baseline SQLite schema with `documents`, `documents_fts`, and generated array-facet tables.
- Prepared-statement inserts inside explicit transactions.
- Final database file with manifest containing database hash, byte size, page count, config hash, and schema version.
- Local smoke query after compile to prove the generated database can answer at least one FTS query and one filtered query.

Exit criteria:

- A fixture static site compiles into a valid SQLite database and manifest.
- The database opens with Python `sqlite3` and returns known results from FTS and facet queries.
- Invalid config, missing required facets, and malformed facet values fail with actionable file paths.
- Running compile twice against unchanged input produces stable document ids and a stable manifest hash.
- No browser runtime work is required to complete this milestone.

### Milestone 1: Compiler Correctness Hardening

Status: complete.

Deliverables:

- `dredge validate`.
- Deterministic file discovery.
- HTML extraction pipeline.
- Typed facet normalization.
- Structured build errors and warnings.
- Small fixture integration tests.

Exit criteria:

- Invalid configuration fails before output.
- Fixture pages compile deterministically.
- Extraction does not retain full site content in memory.

### Milestone 2: SQLite Schema, FTS, And Indexing

Status: complete.

Deliverables:

- Generated document and facet schema.
- Contentless FTS5 table.
- Generated scalar and array facet indexes.
- Finalization with `ANALYZE`, FTS optimize, and `VACUUM INTO`.
- Query plan verification for representative filters.

Exit criteria:

- Known result and facet tests pass.
- Final database is compact and read-only compatible.
- Composite indexes improve or preserve measured query plans.

### Milestone 3: Query Engine And Code Generation

Status: complete.

Implemented behavior: empty queries skip FTS and paginate deterministically by document id; non-empty user queries are tokenized, quoted, and bound as FTS parameters; filters are generated only from validated facet identifiers and bound values; scalar multi-select filters use OR semantics; array filters use `EXISTS`; numeric and date ranges are inclusive; facet counts are computed after active query and filters are applied.

Deliverables:

- Safe query builder.
- Generated TypeScript filters and result types.
- Search, pagination, total count, and facet count API.
- Worker message protocol types.
- Stale response handling.

Exit criteria:

- SQL generation tests cover all facet types.
- TypeScript client compiles in a fixture app.
- Empty query, search query, and filtered query behavior is documented and tested.

### Milestone 4: Runtime Validation Gate

Purpose: prove the full-download, Brotli decompression, synchronous OPFS storage, and SQLite open assumptions using the real database artifact shape produced by the Python compiler.

Deliverables:

- Minimal generated SQLite database downloaded as a Brotli-compressed asset, decompressed, stored in OPFS, and opened read-only through a synchronous-access-handle VFS in a worker.
- Support detection that requires synchronous OPFS access handles and fails loudly when they are missing.
- Support detection for current Chrome, Edge, Safari, and Firefox.
- Two-tab read-only query test, including concurrent first-boot download convergence.
- Runtime measurements against a compiler-generated database.
- Decision on VFS choice and any required database schema adjustments.

Exit criteria:

- The synchronous-access-handle OPFS VFS opens the decompressed database reliably on the target supported browsers, or an alternate runtime strategy is selected.
- Browsers without synchronous OPFS access handles fail fast with `UNSUPPORTED_SYNC_ACCESS`.
- Multi-tab read-only access is correct or the product scope is adjusted.
- First-boot download, decompression, and OPFS write timings, plus warm-boot timings, are within adjustable production budgets.

Status: validated against a real 150,000-page compiler-generated database in a Chromium worker (Electron 42 / Chrome 148) via the `runtime/` harness.

Measured results (synthetic 150k corpus; uncompressed DB 90.23 MB, Brotli 25.39 MB; SQLite page size 16 KB; read-only open with `cache_size = -131072`, `temp_store = MEMORY`, `query_only = 1`):

- Cold boot total ~1.04 s — manifest 5.7 ms, download 700 ms (transparent `Content-Encoding: br` in dev), OPFS write 311 ms, SQLite open 22 ms.
- Warm boot total ~11 ms — `fromCache: true`, no download, no OPFS write, SQLite open ~6 ms.
- Warm query p50 / p95 / p99 (25 timed runs each, one untimed warmup):
  - Point lookup (1 match): 1.5 / 4.8 / 8.1 ms.
  - Selective search (~150 matches): 3.3 / 4.8 / 5.0 ms.
  - Moderate search (~3,000 matches): 7.6 / 9.3 / 10.6 ms.
  - Selective search plus scalar filters: 5.7 / 8.6 / 23.0 ms.
  - Facet category counts (full `GROUP BY`): 12.7 / 17.8 / 20.9 ms.
  - Array-facet `EXISTS` filter: 2.3 / 8.6 / 11.1 ms.
  - Broad search (~all 150k matches, worst case): 138 / 184 / 196 ms.
- One-time cold first ranked query (FTS index page-in plus global stats): ~1.6 s, paid once per session before the page cache is warm.

Key findings:

- The default page cache (~8 MB) thrashes catastrophically against a 90 MB database over OPFS sync access handles; a broad-term ranked query exceeded 160 s. Setting a database-sized page cache (`cache_size = -131072`, 128 MB) is mandatory and brought broad-search p95 to under 200 ms.
- All realistic (point, selective, moderate, filtered, facet) queries meet the production budgets below. Only the deliberately pathological broad-term case (a single token matching nearly every document) and the one-time cold first query exceed the steady-state search budget; both are expected and acceptable.
- Reloading the page while a worker still holds OPFS sync access handles causes `NoModificationAllowedError` from the SAH pool; the runtime must tear down the open database (and the worker) before re-acquiring handles.

### Milestone 5: Runtime Storage And Worker Productionization

Deliverables:

- Manifest fetch and compatibility validation.
- Full database download, Brotli decompression, synchronous OPFS writes, and obsolete database cleanup.
- Read-only OPFS-backed SQLite open path.
- Typed state machine and typed errors.
- Worker bundle and WASM assets built with `pnpm` and Vite, emitted with content-addressed filenames into `output_dir`.
- Browser tests for first boot, warm boot, failure paths, and multi-tab.

Exit criteria:

- Unsupported runtimes fail before downloading or opening the database.
- Warm boot avoids any database download when a valid OPFS database exists.
- Corrupt or partial stored databases recover once and then fail loudly if still invalid.

### Milestone 6: Stress Testing And Performance Tuning

Deliverables:

- Synthetic 150,000+ page generator.
- Repeatable benchmark runner.
- Build memory and duration reports.
- Compiler and runtime latency reports.
- Index tuning based on measured query plans.

Exit criteria:

- Stress dataset meets the agreed production budgets.
- Performance results are saved as artifacts and compared across changes.
- Any missed budget has a documented decision: optimize, reduce scope, or change architecture.

### Milestone 7: Packaging, Documentation, And Release Readiness

Deliverables:

- CLI documentation.
- Configuration reference.
- Browser support matrix.
- Hosting and CSP guide.
- Runtime error handling guide.
- Example integration.
- Release checklist.

Exit criteria:

- A new static site can integrate Dredge from documentation alone.
- All generated assets and cache behavior are documented.
- Known limitations are explicit.

---

## 15. Key Risks And Decisions

| Risk | Mitigation |
| --- | --- |
| Synchronous OPFS access handles are unavailable in a required browser. | Milestone 4 blocks runtime implementation until verified. The runtime fails fast and loud with `UNSUPPORTED_SYNC_ACCESS` and never silently degrades. |
| Static hosting or CDN behavior alters the compressed database bytes. | Use content-addressed `.db.br` filenames and verify decompressed bytes against `db_bytes` before opening SQLite. Document required hosting settings. |
| Full database download is large on first boot. | Brotli-compress the database for transfer, measure compression ratio, and store the decompressed database in OPFS so the download happens at most once per database version. |
| Facet counts are slower than result search. | Measure query plans, add generated covering indexes, restrict initial count semantics, or make selected facets explicit. |
| Static hosting cache headers cannot be controlled. | Use content-addressed filenames and fetch the manifest with cache revalidation for database identity checks. |
| Multi-tab first-boot downloads cause intermittent failures. | Coordinate so only one tab promotes the final OPFS database, add bounded retries, and gate on browser tests. |
| Query syntax causes FTS errors for normal user input. | Default to Dredge-managed tokenization and escaping, with raw FTS syntax disabled. |
| Build memory grows with site size. | Stream extraction, batch inserts, avoid retaining bodies, and enforce stress memory budgets. |

---

## 16. Implementation Readiness Checklist

- The architecture has a static asset contract.
- The configuration schema is explicit enough to implement.
- The database schema has a concrete first version.
- Runtime downloads the full Brotli-compressed database and stores the decompressed database in OPFS via synchronous access handles.
- Runtime storage invalidation is defined through content hashes and OPFS namespaces.
- Hosting requirements for the compressed database asset are explicit.
- Browser unsupported states are typed and fail before downloading or opening the database.
- Query safety rules are explicit.
- Performance claims are replaced with measurable acceptance targets.
- The 150,000+ page stress path is part of the plan, not a later afterthought.

This plan is ready for implementation, starting with Milestone 0: the Python compiler MVP.
