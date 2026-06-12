/// <reference lib="webworker" />

import sqlite3InitModule from "@sqlite.org/sqlite-wasm";

import type { BootTimings, DredgeError, DredgeManifest, DredgeStatus } from "./protocol";

// Name of the OPFS SAH pool VFS. Files imported into the pool live under this
// namespace inside OPFS.
const VFS_NAME = "dredge-sahpool";

export type StatusFn = (status: DredgeStatus, detail?: string) => void;

export class WorkerError extends Error {
  readonly code: string;
  readonly details?: unknown;
  constructor(error: DredgeError) {
    super(error.message);
    this.code = error.code;
    this.details = error.details;
  }
}

export function toDredgeError(error: unknown): DredgeError {
  if (error instanceof WorkerError) {
    return { code: error.code, message: error.message, details: error.details };
  }
  if (error instanceof Error) {
    return { code: "QUERY_FAILED", message: error.message };
  }
  return { code: "QUERY_FAILED", message: String(error) };
}

export type Exec = (sql: string, bind?: unknown[]) => unknown[][];

interface OpenDatabase {
  db: unknown;
  manifest: DredgeManifest;
  exec: Exec;
}

let sqlite3: any;
let poolUtil: any;
let opened: OpenDatabase | undefined;

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

async function decompress(compressed: Uint8Array, manifest: DredgeManifest): Promise<Uint8Array> {
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

function openDatabaseHandle(path: string): unknown {
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

function makeExec(db: any): Exec {
  return (sql: string, bind: unknown[] = []) => {
    return db.exec({ sql, bind, returnValue: "resultRows", rowMode: "array" }) as unknown[][];
  };
}

export function closeDatabase(): void {
  if (opened) {
    try {
      (opened.db as any).close();
    } catch {
      // ignore
    }
    opened = undefined;
  }
}

export function getExec(): Exec {
  if (!opened) {
    throw new WorkerError({ code: "QUERY_FAILED", message: "Database is not open." });
  }
  return opened.exec;
}

export function getManifest(): DredgeManifest | undefined {
  return opened?.manifest;
}

export async function boot(manifestUrl: string, reset: boolean, status: StatusFn): Promise<BootTimings> {
  status("checking_support");
  assertSyncAccessHandleSupport();
  await ensureSqlite();

  const t0 = performance.now();
  status("fetching_manifest");
  const manifest = await fetchManifest(manifestUrl);
  const manifestDone = performance.now();

  const path = dbPathFor(manifest);
  if (reset) {
    closeDatabase();
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
  closeDatabase();
  const db = openDatabaseHandle(path);
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
