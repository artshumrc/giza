// Shared message protocol + types for the Dredge Milestone 4 validation harness.
// This intentionally mirrors the generated client protocol shape but adds
// benchmark-specific messages used only by the harness.

export interface DredgeManifest {
  manifest_version: number;
  db_schema_version: number;
  db_file: string;
  db_sha256: string;
  db_bytes: number;
  db_compressed_bytes: number;
  db_compression: string;
  sqlite_page_size: number;
  page_count: number;
  config_hash: string;
  runtime_min_version: string;
}

export type DredgeStatus =
  | "idle"
  | "checking_support"
  | "fetching_manifest"
  | "checking_storage"
  | "downloading_db"
  | "decompressing_db"
  | "writing_opfs"
  | "opening_db"
  | "ready"
  | "failed";

export type DredgeErrorCode =
  | "UNSUPPORTED_OPFS"
  | "UNSUPPORTED_SYNC_ACCESS"
  | "MANIFEST_FETCH_FAILED"
  | "RUNTIME_VERSION_MISMATCH"
  | "DB_DOWNLOAD_FAILED"
  | "DB_DECOMPRESS_FAILED"
  | "DB_SIZE_MISMATCH"
  | "DB_STORAGE_CORRUPT"
  | "QUOTA_EXCEEDED"
  | "SQLITE_OPEN_FAILED"
  | "SQLITE_BUSY_LOCKED"
  | "QUERY_FAILED";

export interface DredgeError {
  code: DredgeErrorCode | string;
  message: string;
  details?: unknown;
}

export interface BootTimings {
  fromCache: boolean;
  manifestMs: number;
  downloadMs: number;
  decompressMs: number;
  writeOpfsMs: number;
  openMs: number;
  totalMs: number;
  compressedBytes: number;
  decompressedBytes: number;
}

export interface QueryTiming {
  label: string;
  sql: string;
  runs: number;
  rows: number;
  p50Ms: number;
  p95Ms: number;
  p99Ms: number;
  minMs: number;
  maxMs: number;
}

export interface BenchmarkReport {
  boot: BootTimings;
  queries: QueryTiming[];
  userAgent: string;
}

export type WorkerRequest =
  | { type: "init"; id: number; manifestUrl: string; reset?: boolean }
  | { type: "benchmark"; id: number; runsPerQuery?: number }
  | { type: "destroy"; id: number };

export type WorkerResponse =
  | { type: "status"; status: DredgeStatus; detail?: string }
  | { type: "ready"; id: number; boot: BootTimings }
  | { type: "benchmarkResult"; id: number; report: BenchmarkReport }
  | { type: "error"; id?: number; error: DredgeError };
