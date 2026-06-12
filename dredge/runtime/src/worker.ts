/// <reference lib="webworker" />

import sqlite3InitModule from "@sqlite.org/sqlite-wasm";

import type {
  BenchmarkReport,
  BootTimings,
  DredgeError,
  DredgeManifest,
  DredgeStatus,
  QueryTiming,
  WorkerRequest,
  WorkerResponse,
} from "./protocol";

// Name of the OPFS SAH pool VFS. Files imported into the pool live under this
// namespace inside OPFS.
const VFS_NAME = "dredge-sahpool";

interface OpenDatabase {
  db: unknown;
  manifest: DredgeManifest;
  exec: (sql: string, bind?: unknown[]) => unknown[][];
}

let sqlite3: any;
let poolUtil: any;
let opened: OpenDatabase | undefined;
let lastBoot: BootTimings | undefined;

function post(message: WorkerResponse): void {
  (self as DedicatedWorkerGlobalScope).postMessage(message);
}

function status(status: DredgeStatus, detail?: string): void {
  post({ type: "status", status, detail });
}

class WorkerError extends Error {
  readonly code: string;
  readonly details?: unknown;
  constructor(error: DredgeError) {
    super(error.message);
    this.code = error.code;
    this.details = error.details;
  }
}

function toDredgeError(error: unknown): DredgeError {
  if (error instanceof WorkerError) {
    return { code: error.code, message: error.message, details: error.details };
  }
  if (error instanceof Error) {
    return { code: "QUERY_FAILED", message: error.message };
  }
  return { code: "QUERY_FAILED", message: String(error) };
}

function assertSyncAccessHandleSupport(): void {
  // The most performant OPFS path requires synchronous access handles inside a
  // worker. Fail fast and loud if they are unavailable rather than degrading.
  const proto = (globalThis as any).FileSystemFileHandle?.prototype;
  if (typeof proto?.createSyncAccessHandle !== "function") {
    throw new WorkerError({
      code: "UNSUPPORTED_SYNC_ACCESS",
      message:
        "FileSystemFileHandle.createSyncAccessHandle is unavailable in this worker. " +
        "Dredge requires synchronous OPFS access handles.",
    });
  }
  if (typeof navigator === "undefined" || typeof navigator.storage?.getDirectory !== "function") {
    throw new WorkerError({
      code: "UNSUPPORTED_OPFS",
      message: "navigator.storage.getDirectory is unavailable; OPFS is required.",
    });
  }
}

async function ensureSqlite(): Promise<void> {
  if (sqlite3) {
    return;
  }
  try {
    sqlite3 = await sqlite3InitModule();
  } catch (error) {
    throw new WorkerError({
      code: "SQLITE_OPEN_FAILED",
      message: `Failed to initialize SQLite WASM: ${(error as Error).message}`,
    });
  }
  if (typeof sqlite3.installOpfsSAHPoolVfs !== "function") {
    throw new WorkerError({
      code: "UNSUPPORTED_SYNC_ACCESS",
      message: "This SQLite build does not provide the OPFS SyncAccessHandle pool VFS.",
    });
  }
  try {
    poolUtil = await sqlite3.installOpfsSAHPoolVfs({ name: VFS_NAME });
  } catch (error) {
    throw new WorkerError({
      code: "UNSUPPORTED_SYNC_ACCESS",
      message: `Failed to install OPFS SAH pool VFS: ${(error as Error).message}`,
    });
  }
}

async function fetchManifest(manifestUrl: string): Promise<DredgeManifest> {
  let response: Response;
  try {
    response = await fetch(manifestUrl, { cache: "no-cache" });
  } catch (error) {
    throw new WorkerError({
      code: "MANIFEST_FETCH_FAILED",
      message: `Failed to fetch manifest: ${(error as Error).message}`,
    });
  }
  if (!response.ok) {
    throw new WorkerError({
      code: "MANIFEST_FETCH_FAILED",
      message: `Manifest request returned HTTP ${response.status}`,
    });
  }
  try {
    return (await response.json()) as DredgeManifest;
  } catch (error) {
    throw new WorkerError({
      code: "MANIFEST_FETCH_FAILED",
      message: `Manifest is not valid JSON: ${(error as Error).message}`,
    });
  }
}

function dbPathFor(manifest: DredgeManifest): string {
  // Namespace the stored database by its content hash so a new database never
  // collides with a stale one.
  return `/dredge/${manifest.db_sha256}.db`;
}

function poolHasFile(path: string): boolean {
  try {
    const names: string[] = poolUtil.getFileNames();
    return names.includes(path);
  } catch {
    return false;
  }
}

async function downloadCompressed(manifest: DredgeManifest, baseUrl: string): Promise<Uint8Array> {
  const url = new URL(manifest.db_file, baseUrl).toString();
  let response: Response;
  try {
    response = await fetch(url, { cache: "force-cache" });
  } catch (error) {
    throw new WorkerError({
      code: "DB_DOWNLOAD_FAILED",
      message: `Failed to download database: ${(error as Error).message}`,
    });
  }
  if (!response.ok) {
    throw new WorkerError({
      code: "DB_DOWNLOAD_FAILED",
      message: `Database request returned HTTP ${response.status}`,
    });
  }
  const buffer = await response.arrayBuffer();
  return new Uint8Array(buffer);
}

async function decompress(
  compressed: Uint8Array,
  manifest: DredgeManifest,
): Promise<Uint8Array> {
  // If the host transparently decoded Content-Encoding: br, the bytes will
  // already match db_bytes and we skip the in-worker decode.
  if (compressed.byteLength === manifest.db_bytes) {
    return compressed;
  }
  let decompressed: Uint8Array;
  try {
    const brotli = await (await import("brotli-wasm")).default;
    decompressed = brotli.decompress(compressed);
  } catch (error) {
    throw new WorkerError({
      code: "DB_DECOMPRESS_FAILED",
      message: `Brotli decompression failed: ${(error as Error).message}`,
    });
  }
  if (decompressed.byteLength !== manifest.db_bytes) {
    throw new WorkerError({
      code: "DB_SIZE_MISMATCH",
      message: `Decompressed database is ${decompressed.byteLength} bytes; manifest expects ${manifest.db_bytes}.`,
    });
  }
  return decompressed;
}

function cleanupStaleDatabases(keepPath: string): void {
  try {
    const names: string[] = poolUtil.getFileNames();
    for (const name of names) {
      if (name.startsWith("/dredge/") && name !== keepPath) {
        try {
          poolUtil.unlink(name);
        } catch {
          // Best-effort cleanup; ignore failures.
        }
      }
    }
  } catch {
    // Ignore — cleanup is non-critical.
  }
}

function openDatabase(path: string): unknown {
  try {
    // OpfsSAHPoolDb opens a database file that lives inside the SAH pool.
    const db = new poolUtil.OpfsSAHPoolDb(path);
    // Read-only workload tuning: a large page cache avoids re-reading pages
    // through the (relatively expensive) OPFS sync-access-handle path during
    // large FTS doclist scans, and temp tables/sorts stay in memory.
    db.exec("PRAGMA cache_size = -131072"); // 128 MB, enough to hold the whole DB
    db.exec("PRAGMA temp_store = MEMORY");
    db.exec("PRAGMA query_only = 1");
    return db;
  } catch (error) {
    throw new WorkerError({
      code: "SQLITE_OPEN_FAILED",
      message: `Failed to open database: ${(error as Error).message}`,
    });
  }
}

function makeExec(db: any): (sql: string, bind?: unknown[]) => unknown[][] {
  return (sql: string, bind: unknown[] = []) => {
    return db.exec({ sql, bind, returnValue: "resultRows", rowMode: "array" }) as unknown[][];
  };
}

async function init(manifestUrl: string, reset: boolean): Promise<BootTimings> {
  status("checking_support");
  assertSyncAccessHandleSupport();
  await ensureSqlite();

  const t0 = performance.now();
  status("fetching_manifest");
  const manifest = await fetchManifest(manifestUrl);
  const manifestDone = performance.now();

  const path = dbPathFor(manifest);
  if (reset) {
    // Release any open database before mutating the stored file.
    if (opened) {
      try {
        (opened.db as any).close();
      } catch {
        // ignore
      }
      opened = undefined;
    }
    if (poolHasFile(path)) {
      try {
        poolUtil.unlink(path);
      } catch {
        // ignore
      }
    }
  }

  status("checking_storage");
  const cached = poolHasFile(path);

  let downloadMs = 0;
  let decompressMs = 0;
  let writeOpfsMs = 0;
  let compressedBytes = manifest.db_compressed_bytes;
  let decompressedBytes = manifest.db_bytes;

  if (!cached) {
    status("downloading_db");
    const downloadStart = performance.now();
    const manifestBase = new URL(manifestUrl, self.location.href).toString();
    const compressed = await downloadCompressed(manifest, manifestBase);
    const downloadEnd = performance.now();
    downloadMs = downloadEnd - downloadStart;
    compressedBytes = compressed.byteLength;

    status("decompressing_db");
    const decompressStart = performance.now();
    const raw = await decompress(compressed, manifest);
    const decompressEnd = performance.now();
    decompressMs = decompressEnd - decompressStart;
    decompressedBytes = raw.byteLength;

    status("writing_opfs");
    const writeStart = performance.now();
    try {
      poolUtil.importDb(path, raw);
    } catch (error) {
      throw new WorkerError({
        code: "QUOTA_EXCEEDED",
        message: `Failed to store database in OPFS: ${(error as Error).message}`,
      });
    }
    writeOpfsMs = performance.now() - writeStart;
    cleanupStaleDatabases(path);
  }

  status("opening_db");
  const openStart = performance.now();
  if (opened) {
    try {
      (opened.db as any).close();
    } catch {
      // ignore
    }
    opened = undefined;
  }
  const db = openDatabase(path);
  const openMs = performance.now() - openStart;

  opened = { db, manifest, exec: makeExec(db) };
  status("ready");

  const totalMs = performance.now() - t0;
  return {
    fromCache: cached,
    manifestMs: manifestDone - t0,
    downloadMs,
    decompressMs,
    writeOpfsMs,
    openMs,
    totalMs,
    compressedBytes,
    decompressedBytes,
  };
}

function percentile(sorted: number[], p: number): number {
  if (sorted.length === 0) {
    return 0;
  }
  const index = Math.min(sorted.length - 1, Math.ceil((p / 100) * sorted.length) - 1);
  return sorted[Math.max(0, index)];
}

function timeQuery(
  label: string,
  sql: string,
  bind: unknown[],
  runs: number,
  warmup = false,
): QueryTiming {
  if (!opened) {
    throw new WorkerError({ code: "QUERY_FAILED", message: "Database is not open." });
  }
  const exec = (): unknown[][] => {
    try {
      return opened!.exec(sql, bind);
    } catch (error) {
      console.error(`[bench] query "${label}" failed:`, error);
      throw new WorkerError({
        code: "QUERY_FAILED",
        message: `Query "${label}" failed: ${(error as Error).message}`,
      });
    }
  };
  const samples: number[] = [];
  let rows = 0;
  // Optional untimed warmup so steady-state percentiles exclude the cold
  // (page-in + FTS global stats) penalty, which is reported separately.
  if (warmup) {
    exec();
  }
  for (let i = 0; i < runs; i += 1) {
    const start = performance.now();
    const result = exec();
    samples.push(performance.now() - start);
    rows = result.length;
  }
  samples.sort((a, b) => a - b);
  return {
    label,
    sql,
    runs,
    rows,
    p50Ms: percentile(samples, 50),
    p95Ms: percentile(samples, 95),
    p99Ms: percentile(samples, 99),
    minMs: samples[0],
    maxMs: samples[samples.length - 1],
  };
}

function runBenchmark(runsPerQuery: number): BenchmarkReport {
  if (!opened) {
    throw new WorkerError({ code: "QUERY_FAILED", message: "Database is not open." });
  }

  const runs = Math.max(1, runsPerQuery);
  const queries: QueryTiming[] = [];

  // Idiomatic FTS5 ranked-search query (top-N by bm25 with deterministic
  // tie-breaker), joined back to the document row for result fields.
  const ranked = `SELECT d.id, d.url, d.title, bm25(documents_fts) AS rank
       FROM documents_fts JOIN documents d ON d.id = documents_fts.rowid
       WHERE documents_fts MATCH ?
       ORDER BY rank, d.id LIMIT 20`;

  // Cold first query: the very first ranked search after open pays a one-time
  // penalty (paging the FTS index in from OPFS + computing global stats).
  // Measured once, with no warmup, against a broad term.
  queries.push(timeQuery("cold_first_search", ranked, ["ancient"], 1, false));

  // --- Warm steady-state (each warmed once, then timed `runs` times) ---

  // Empty query / pagination straight off the documents table.
  queries.push(
    timeQuery(
      "empty_paginate",
      "SELECT id, url, title FROM documents ORDER BY id LIMIT 20 OFFSET 1000",
      [],
      runs,
      true,
    ),
  );

  // Point lookup: a single matching document (most selective FTS case).
  queries.push(timeQuery("point_lookup", ranked, ["uid77777"], runs, true));

  // Selective search: ~count/1000 matches (~150 docs at 150k).
  queries.push(timeQuery("selective_search", ranked, ["grp42"], runs, true));

  // Moderate search: ~count/50 matches (~3000 docs at 150k).
  queries.push(timeQuery("moderate_search", ranked, ["cohort7"], runs, true));

  // Broad search: a near-ubiquitous term (~all docs) — worst case for ranking.
  queries.push(timeQuery("broad_search", ranked, ["ancient"], runs, true));

  // Selective search + scalar filters (composite index path).
  queries.push(
    timeQuery(
      "filtered_search",
      `SELECT d.id, d.url, d.title, bm25(documents_fts) AS rank
       FROM documents_fts JOIN documents d ON d.id = documents_fts.rowid
       WHERE documents_fts MATCH ? AND d.category = ? AND d.year BETWEEN ? AND ?
       ORDER BY rank, d.id LIMIT 20`,
      ["cohort7", "object", 2010, 2024],
      runs,
      true,
    ),
  );

  // Facet counts: full GROUP BY scan of the documents table.
  queries.push(
    timeQuery(
      "facet_category_counts",
      "SELECT category, COUNT(*) AS n FROM documents GROUP BY category ORDER BY n DESC",
      [],
      runs,
      true,
    ),
  );

  // Array-facet filter via EXISTS against the generated join table.
  queries.push(
    timeQuery(
      "array_facet_filter",
      `SELECT d.id, d.url
       FROM documents d
       WHERE EXISTS (SELECT 1 FROM facet_tags ft WHERE ft.document_id = d.id AND ft.value = ?)
       ORDER BY d.id LIMIT 20`,
      ["royal"],
      runs,
      true,
    ),
  );

  return {
    boot: lastBoot ?? {
      fromCache: false,
      manifestMs: 0,
      downloadMs: 0,
      decompressMs: 0,
      writeOpfsMs: 0,
      openMs: 0,
      totalMs: 0,
      compressedBytes: 0,
      decompressedBytes: 0,
    },
    queries,
    userAgent: navigator.userAgent,
  };
}

self.onmessage = async (event: MessageEvent<WorkerRequest>) => {
  const message = event.data;
  try {
    if (message.type === "init") {
      const boot = await init(message.manifestUrl, message.reset ?? false);
      lastBoot = boot;
      post({ type: "ready", id: message.id, boot });
      return;
    }
    if (message.type === "benchmark") {
      const report = runBenchmark(message.runsPerQuery ?? 25);
      post({ type: "benchmarkResult", id: message.id, report });
      return;
    }
    if (message.type === "destroy") {
      if (opened) {
        try {
          (opened.db as any).close();
        } catch {
          // ignore
        }
        opened = undefined;
      }
      return;
    }
  } catch (error) {
    status("failed");
    post({ type: "error", id: (message as { id?: number }).id, error: toDredgeError(error) });
  }
};
