// Dredge browser search client.
//
// Part of the standalone Dredge library: a headless, framework-free client that
// owns the search Web Worker (SQLite/FTS5 over OPFS) and exposes a small async
// API. Bundled to `dredge-client.js` and consumed by any static site.
//
// This module is type-only with respect to the worker — it never imports the
// worker or SQLite code, so the client bundle stays tiny and the heavy WASM is
// loaded lazily inside the worker the first time `init()`/`search()` runs.

import type {
  DredgeSearchRequest,
  DredgeSearchResponse,
} from "./search";

export type {
  DredgeFilters,
  DredgeFilterValue,
  DredgeRange,
  DredgeHit,
  DredgeFacetBucket,
  DredgeSearchRequest,
  DredgeSearchResponse,
} from "./search";

const DEFAULT_WORKER_URL = "/search/dredge-worker.js";
const DEFAULT_MANIFEST_URL = "/search/search-manifest.json";

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

export interface DredgeError {
  code: string;
  message: string;
  details?: unknown;
}

type WorkerResponse =
  | { type: "status"; status: DredgeStatus; detail?: string }
  | { type: "ready"; id: number }
  | { type: "searchResult"; id: number; response: DredgeSearchResponse }
  | { type: "error"; id?: number; error: DredgeError };

export class DredgeClientError extends Error {
  readonly code: string;
  readonly details?: unknown;
  constructor(error: DredgeError) {
    super(error.message);
    this.name = "DredgeClientError";
    this.code = error.code;
    this.details = error.details;
  }
}

export interface DredgeClientOptions {
  /** URL of the bundled Dredge worker script. Defaults to /search/dredge-worker.js */
  workerUrl?: string | URL;
  /** URL of the search manifest JSON. Defaults to /search/search-manifest.json */
  manifestUrl?: string;
  /** Force re-download/import of the database even if cached in OPFS. */
  reset?: boolean;
  /** Override worker construction (useful for tests / custom bundlers). */
  workerFactory?: (url: string | URL) => Worker;
}

type Pending =
  | { kind: "init"; resolve: () => void; reject: (error: DredgeClientError) => void }
  | {
      kind: "search";
      resolve: (response: DredgeSearchResponse) => void;
      reject: (error: DredgeClientError) => void;
    };

/**
 * Headless Dredge search client.
 *
 * Lifecycle: the first `search()` (or an explicit `init()`) boots the worker,
 * which downloads + decompresses the database into OPFS and opens it. Repeat
 * visits reuse the OPFS copy. Searches are debounced by recency: when a newer
 * search is issued, older in-flight searches reject with a `STALE_RESPONSE`
 * error so callers can safely ignore superseded queries.
 */
export class DredgeSearchClient {
  private readonly workerUrl: string | URL;
  private readonly manifestUrl: string;
  private readonly reset: boolean;
  private readonly workerFactory?: (url: string | URL) => Worker;
  private worker: Worker | undefined;
  private statusValue: DredgeStatus = "idle";
  private initPromise: Promise<void> | undefined;
  private nextId = 1;
  private latestSearchId = 0;
  private readonly pending = new Map<number, Pending>();
  private readonly statusListeners = new Set<(status: DredgeStatus) => void>();

  constructor(options: DredgeClientOptions = {}) {
    this.workerUrl = options.workerUrl ?? DEFAULT_WORKER_URL;
    this.manifestUrl = options.manifestUrl ?? DEFAULT_MANIFEST_URL;
    this.reset = options.reset ?? false;
    this.workerFactory = options.workerFactory;
  }

  get status(): DredgeStatus {
    return this.statusValue;
  }

  /** Subscribe to status changes. Returns an unsubscribe function. */
  onStatus(listener: (status: DredgeStatus) => void): () => void {
    this.statusListeners.add(listener);
    listener(this.statusValue);
    return () => {
      this.statusListeners.delete(listener);
    };
  }

  /** Boot the worker and open the database. Safe to call repeatedly. */
  init(): Promise<void> {
    if (this.statusValue === "ready") {
      return Promise.resolve();
    }
    if (this.initPromise) {
      return this.initPromise;
    }
    const worker = this.ensureWorker();
    const id = this.nextId++;
    this.setStatus("checking_support");
    this.initPromise = new Promise<void>((resolve, reject) => {
      this.pending.set(id, { kind: "init", resolve, reject });
      worker.postMessage({ type: "init", id, manifestUrl: this.manifestUrl, reset: this.reset });
    }).finally(() => {
      this.initPromise = undefined;
    });
    return this.initPromise;
  }

  /** Execute a search. Boots the worker on first use. */
  async search(request: DredgeSearchRequest = {}): Promise<DredgeSearchResponse> {
    await this.init();
    const worker = this.ensureWorker();
    const id = this.nextId++;
    this.rejectOlderSearches(id);
    this.latestSearchId = id;
    return new Promise<DredgeSearchResponse>((resolve, reject) => {
      this.pending.set(id, { kind: "search", resolve, reject });
      worker.postMessage({ type: "search", id, request });
    });
  }

  /** Tear down the worker and reject all pending work. */
  destroy(): void {
    if (this.worker) {
      try {
        this.worker.postMessage({ type: "destroy", id: this.nextId++ });
      } catch {
        // ignore
      }
      this.worker.terminate();
      this.worker = undefined;
    }
    this.rejectAll({ code: "WORKER_TERMINATED", message: "Dredge worker was terminated." });
    this.initPromise = undefined;
    this.latestSearchId = 0;
    this.setStatus("idle");
  }

  private ensureWorker(): Worker {
    if (this.worker) {
      return this.worker;
    }
    const worker = this.workerFactory
      ? this.workerFactory(this.workerUrl)
      : new Worker(this.workerUrl, { type: "module" });
    worker.addEventListener("message", this.handleMessage);
    worker.addEventListener("error", this.handleWorkerError);
    this.worker = worker;
    return worker;
  }

  private readonly handleMessage = (event: MessageEvent<WorkerResponse>): void => {
    const message = event.data;
    if (message.type === "status") {
      this.setStatus(message.status);
      return;
    }
    if (message.type === "ready") {
      this.setStatus("ready");
      const pending = this.pending.get(message.id);
      if (pending?.kind === "init") {
        this.pending.delete(message.id);
        pending.resolve();
      }
      return;
    }
    if (message.type === "searchResult") {
      const pending = this.pending.get(message.id);
      if (pending?.kind === "search") {
        this.pending.delete(message.id);
        pending.resolve(message.response);
      }
      return;
    }
    if (message.type === "error") {
      const error = new DredgeClientError(message.error);
      if (message.id !== undefined && this.pending.has(message.id)) {
        const pending = this.pending.get(message.id)!;
        this.pending.delete(message.id);
        pending.reject(error);
        if (pending.kind === "init") {
          this.fail(message.error);
        }
        return;
      }
      this.fail(message.error);
    }
  };

  private readonly handleWorkerError = (): void => {
    this.fail({ code: "WORKER_ERROR", message: "Dredge worker failed." });
  };

  private rejectOlderSearches(newestId: number): void {
    for (const [id, pending] of this.pending) {
      if (pending.kind === "search" && id < newestId) {
        this.pending.delete(id);
        pending.reject(
          new DredgeClientError({
            code: "STALE_RESPONSE",
            message: "A newer Dredge search superseded this request.",
          }),
        );
      }
    }
  }

  private rejectAll(error: DredgeError): void {
    const clientError = new DredgeClientError(error);
    for (const pending of this.pending.values()) {
      pending.reject(clientError);
    }
    this.pending.clear();
  }

  private fail(error: DredgeError): void {
    this.rejectAll(error);
    this.initPromise = undefined;
    this.setStatus("failed");
  }

  private setStatus(status: DredgeStatus): void {
    this.statusValue = status;
    for (const listener of this.statusListeners) {
      listener(status);
    }
  }
}
