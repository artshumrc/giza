# Dredge Production Implementation Plan

Status: Milestone 1 complete. The Python compiler now has a shared validation path, deterministic fixture coverage, typed facet normalization checks, structured build diagnostics, bounded warning aggregation, and local integration tests. Runtime validation remains important, but it follows the hardened compiler artifact because the first useful artifact is the generated database.

Dredge is a compiled, configuration-driven, client-side search system for very large static sites. The target use case is a static site with 150,000+ generated pages, no permanent search server, and rich search plus faceted navigation in supported browsers.

The prior concept is directionally sound, but production readiness requires explicit contracts for configuration, generated assets, database schema, cache invalidation, browser support, query safety, performance budgets, and stress testing. This plan defines those contracts.

---

## 1. Goals

- Build a static SQLite search database from an already-built static site.
- Support 150,000+ HTML pages without keeping all page content in memory.
- Provide full-text search, typed filters, result pagination, and facet counts from the browser.
- Keep runtime search off the main thread by using a Web Worker.
- Cache fetched SQLite pages or aligned byte ranges in the browser's Origin Private File System.
- Fail explicitly on unsupported browsers or storage conditions before opening SQLite, and detect hosts without HTTP Range support with a minimal range probe rather than a full-file transfer.
- Generate a type-safe client API from the exact search configuration.
- Produce deterministic, content-addressed assets that are safe to deploy on static hosting.

---

## 2. Non-Goals For The First Production Version

- No server-hosted search fallback.
- No support for browsers or hosts that cannot support the selected HTTP Range VFS and persistent page cache requirements.
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
        +--> search/search.<db_hash>.db
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
        +--> support check
        +--> manifest fetch
        +--> HTTP Range VFS + OPFS byte-range cache
        +--> read-only SQLite connection
        +--> parameterized search and facet queries
```

The main thread never opens SQLite and never performs database I/O. SQLite access, HTTP Range orchestration, and OPFS page-cache work are isolated inside the worker.

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
| `search.<db_hash>.db` | Immutable SQLite database accessed by HTTP Range requests. | Content-addressed filename. Safe for long-lived static caching when served without byte-transforming compression. |
| `dredge-worker.<hash>.js` | Runtime worker bundle. | Content-addressed filename. |
| `dredge-client.ts` | Generated typed client used by the app. | Committed or generated during the app build. |

Manifest shape:

```json
{
  "manifest_version": 1,
  "db_schema_version": 1,
  "db_file": "search.4f3a1c....db",
  "db_sha256": "4f3a1c...",
  "db_bytes": 73400320,
  "sqlite_page_size": 16384,
  "range_required": true,
  "range_block_bytes": 65536,
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

- The database file is not transferred in full during boot.
- The runtime VFS reads the immutable database using HTTP `Range` requests.
- Fetched SQLite pages or aligned byte ranges are cached in OPFS under a namespace derived from `db_sha256`.
- `db_sha256` identifies the immutable database artifact, but the runtime must not require a full-file hash verification before the first query.
- `range_block_bytes` should be a multiple of `sqlite_page_size` and is the default persistent cache unit.

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
- Expose status changes for boot, manifest fetch, range support probe, cache activity, ready, and failure states.
- Reject searches before readiness with a typed error.
- Assign sequence ids to search requests and discard stale responses from older keystrokes.
- Support debouncing at the application layer rather than hard-coding debounce in the client.
- Terminate the worker via `destroy()`.

---

## 10. Runtime HTTP Range VFS And OPFS Page Cache

### 10.1 Support Detection

The worker must check browser and hosting support before opening SQLite. The only database-byte request allowed during support detection is a minimal HTTP Range probe, such as `Range: bytes=0-0`.

Required support:

- `Worker` module support from the application.
- WebAssembly support required by the selected SQLite runtime.
- HTTP `Range` support for the immutable database asset, verified by a `206 Partial Content` response with a valid `Content-Range`.
- Stable byte offsets for the database asset. The host must not transparently gzip, brotli, or otherwise transform the `.db` bytes served to the range VFS.
- Persistent page-cache storage in the worker. The first production runtime uses OPFS for this cache.
- Any additional OPFS APIs required by the selected range VFS. If the VFS requires synchronous access handles, check `FileSystemFileHandle.createSyncAccessHandle` inside the worker.

Unsupported cases return a typed error to the main thread. They do not throw unstructured errors and do not fetch all database bytes.

### 10.2 HTTP Range And Page Cache Lifecycle

The runtime treats the deployed database file as the source of truth and OPFS as a persistent cache of fetched SQLite pages or aligned byte ranges. It must not seed OPFS by transferring every database byte during first boot.

Boot sequence:

1. Fetch `search-manifest.json` with `cache: "no-cache"`.
2. Validate manifest version and runtime compatibility.
3. Validate browser storage support required by the persistent page cache.
4. Probe the database asset with a one-byte HTTP Range request.
5. Verify `206 Partial Content`, `Content-Range`, total byte length, and untransformed byte serving.
6. Open SQLite read-only through the selected HTTP Range VFS.
7. On each VFS read, align the requested offset and length to cache blocks derived from `range_block_bytes`.
8. Return cached blocks from OPFS when present.
9. Fetch missing blocks with HTTP Range requests, write them to OPFS under the `db_sha256` namespace, and satisfy the SQLite read.
10. Remove obsolete database cache namespaces after the current database is ready or when quota pressure requires eviction.

Cache rules:

- Cache keys include `db_sha256`, byte offset, and byte length.
- Cache writes use temporary keys or files and become visible only after the full range is written.
- Cache blocks should be multiples of the SQLite page size to avoid repeatedly fetching partial pages.
- The runtime may prefetch adjacent blocks after measuring that it improves cold-query behavior.
- The runtime must not require full-file SHA-256 verification before the first query.
- A no-persistent-cache mode is a future explicit feature, not a silent fallback.

Failure recovery:

- A partial cached block is ignored and deleted on the next boot or cache read.
- A range probe that returns `200 OK` for a range request returns `RANGE_NOT_SUPPORTED`.
- A range response with the wrong `Content-Range` or length returns `DB_RANGE_REQUEST_FAILED`.
- A corrupt cached block is evicted and fetched once before returning `RANGE_CACHE_CORRUPT` or the underlying SQLite error.
- Cache quota errors evict obsolete database namespaces first, then least-recently-used blocks if implemented. If the current read still cannot be cached, return `QUOTA_EXCEEDED` rather than silently switching modes.
- Lock contention retries with bounded backoff, then returns `SQLITE_BUSY_LOCKED`.

### 10.3 Multi-Tab Behavior

Use or adapt a maintained HTTP Range-capable SQLite VFS rather than writing a custom VFS first. The selected VFS must support an OPFS-backed persistent page cache or provide clear extension points for one.

Production requirements:

- Two tabs from the same origin can initialize and query without corrupting the database.
- If the VFS serializes cache writes, queries remain correct and errors are typed.
- If the VFS cannot satisfy multi-tab read-only access reliably, Milestone 4 must stop runtime implementation and choose a different runtime strategy.

### 10.4 Worker State Machine

Runtime state should be explicit:

```text
idle
  -> checking_support
  -> fetching_manifest
  -> probing_range_support
  -> opening_range_vfs
  -> ready

While ready, individual queries may enter cache_read, range_fetch, and cache_write substates for missing database pages.

Any state can transition to failed with a typed DredgeError.
```

Typed error codes:

| Code | Meaning |
| --- | --- |
| `UNSUPPORTED_OPFS` | OPFS directory access is missing. |
| `UNSUPPORTED_SYNC_ACCESS` | Sync access handles are unavailable in the worker when required by the selected VFS. |
| `MANIFEST_FETCH_FAILED` | Manifest could not be fetched or parsed. |
| `RUNTIME_VERSION_MISMATCH` | Manifest requires a newer runtime. |
| `RANGE_NOT_SUPPORTED` | The host does not serve the database with valid HTTP Range responses. |
| `DB_SIZE_MISMATCH` | The probed database byte length does not match the manifest. |
| `DB_RANGE_REQUEST_FAILED` | A database range request failed or returned invalid bytes. |
| `RANGE_CACHE_CORRUPT` | A cached range could not be used after one eviction and refetch attempt. |
| `QUOTA_EXCEEDED` | Persistent page-cache writes fail after allowed eviction. |
| `SQLITE_OPEN_FAILED` | SQLite could not open the range-backed database. |
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
| Final DB size | Measured initially in Milestone 0 and stress-tested in Milestone 6. Initial soft target: under 150 MB uncompressed. |
| Unsupported browser failure | Typed failure before opening SQLite or fetching database pages. |
| Host range support | Invalid HTTP Range support is detected with a minimal probe and returns a typed error. |
| Cold range behavior | First load transfers only the manifest, range probe, and SQLite pages needed by actual queries. |
| Warm startup | Ready under 1 second after cache metadata and previously fetched pages are available on a current desktop browser. |
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

- First boot fetches the manifest, probes range support, opens the range VFS, and fetches only pages needed by queries.
- Warm boot reuses OPFS-cached pages and avoids refetching cached ranges.
- Unsupported OPFS path fails before opening SQLite or fetching query pages.
- Private browsing or quota denial returns a typed error.
- Hosts that ignore `Range` and return `200 OK` fail with `RANGE_NOT_SUPPORTED`.
- Corrupt cached ranges are evicted and refetched once.
- No browser test should transfer all database bytes before the first query result unless the query genuinely touches every required page.
- Two tabs query simultaneously.
- Worker termination and recreation do not corrupt cached ranges.

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
- Runtime first-boot timing.
- Runtime warm-boot timing.
- Cold-query range request count and transferred bytes.
- Warm-query cache hit rate and transferred bytes.
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
- Search queries stay local. The network sees only static asset requests for the manifest, worker, WASM, and database byte ranges.
- Diagnostics are exposed to the host app so the app can decide what to log.

Hosting requirements:

- Search assets should be served from the same origin as the app unless CORS is explicitly configured.
- The database asset must support HTTP `Range` requests and return `206 Partial Content` for valid range reads.
- The database asset must be served with stable byte offsets. Do not apply transparent gzip or brotli transformation to the `.db` response used by the range VFS.
- If search assets are cross-origin, CORS must allow range requests and expose `Accept-Ranges`, `Content-Length`, `Content-Range`, and any cache validators used by the runtime.
- Service workers, CDNs, and static-host rewrites must not collapse database range requests into full-file responses.
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

Purpose: prove the HTTP Range VFS, browser storage, and SQLite assumptions using the real database artifact shape produced by the Python compiler.

Deliverables:

- Minimal generated SQLite database opened through the selected HTTP Range-capable SQLite runtime in a worker.
- HTTP Range VFS read-only open path with OPFS-backed page cache.
- Support detection for current Chrome, Edge, Safari, Firefox, and representative static hosting behavior.
- Two-tab read-only query test.
- Runtime measurements against a compiler-generated database.
- Decision on VFS choice and any required database schema adjustments.

Exit criteria:

- HTTP Range VFS plus OPFS page cache works reliably on the target supported browsers and hosting setup, or an alternate runtime strategy is selected.
- Multi-tab read-only access is correct or the product scope is adjusted.
- Cold-query range bytes, range request counts, cache hit rates, and warm-query timings are within adjustable production budgets.

### Milestone 5: Runtime Cache And Worker Productionization

Deliverables:

- Manifest fetch and compatibility validation.
- HTTP Range VFS integration, OPFS page-cache writes, and obsolete cache cleanup.
- Read-only range-backed SQLite open path.
- Typed state machine and typed errors.
- Browser tests for first boot, warm boot, failure paths, and multi-tab.

Exit criteria:

- Unsupported runtimes fail before opening SQLite or fetching query pages.
- Warm boot avoids network fetches for cached database pages.
- Corrupt or partial cached ranges recover once and then fail loudly if still invalid.

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
| HTTP Range VFS or OPFS page caching is not reliable across required browsers. | Milestone 4 blocks runtime implementation until verified or an alternate runtime is selected. |
| Static hosting or CDN behavior breaks range reads. | Probe for `206 Partial Content`, stable `Content-Range`, and untransformed bytes before opening SQLite. Document required hosting settings. |
| Cold queries require too many range requests or bytes. | Measure early, tune SQLite page size, cache block size, FTS detail/tokenizer, indexes, and optional adjacent-block prefetch. |
| Facet counts are slower than result search. | Measure query plans, add generated covering indexes, restrict initial count semantics, or make selected facets explicit. |
| Static hosting cache headers cannot be controlled. | Use content-addressed filenames, fetch the manifest with cache revalidation, and rely on range probes for database identity checks. |
| Multi-tab OPFS page-cache writes cause intermittent failures. | Use maintained cooperative cache coordination, add bounded retries, and gate on browser tests. |
| Query syntax causes FTS errors for normal user input. | Default to Dredge-managed tokenization and escaping, with raw FTS syntax disabled. |
| Build memory grows with site size. | Stream extraction, batch inserts, avoid retaining bodies, and enforce stress memory budgets. |

---

## 16. Implementation Readiness Checklist

- The architecture has a static asset contract.
- The configuration schema is explicit enough to implement.
- The database schema has a concrete first version.
- Runtime uses HTTP Range reads with OPFS-cached SQLite pages or aligned ranges.
- Runtime cache invalidation is defined through content hashes and cache namespaces.
- Hosting requirements for byte-range SQLite access are explicit.
- Browser unsupported states are typed and fail before opening SQLite or fetching query pages.
- Query safety rules are explicit.
- Performance claims are replaced with measurable acceptance targets.
- The 150,000+ page stress path is part of the plan, not a later afterthought.

This plan is ready for implementation, starting with Milestone 0: the Python compiler MVP.
