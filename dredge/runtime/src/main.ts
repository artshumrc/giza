import type { BenchmarkReport, BootTimings, WorkerResponse } from "./protocol";

const MANIFEST_URL = "/search/search-manifest.json";

const statusEl = document.querySelector<HTMLElement>("#status")!;
const logEl = document.querySelector<HTMLElement>("#log")!;
const bootEl = document.querySelector<HTMLElement>("#boot")!;
const queriesEl = document.querySelector<HTMLElement>("#queries")!;
const runColdBtn = document.querySelector<HTMLButtonElement>("#run-cold")!;
const runWarmBtn = document.querySelector<HTMLButtonElement>("#run-warm")!;

let worker: Worker | undefined;
let requestId = 0;

function log(line: string): void {
  const time = new Date().toISOString().slice(11, 23);
  logEl.textContent = `[${time}] ${line}\n${logEl.textContent ?? ""}`;
}

function fmt(ms: number): string {
  return `${ms.toFixed(1)} ms`;
}

function fmtBytes(bytes: number): string {
  if (bytes >= 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  }
  if (bytes >= 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${bytes} B`;
}

function renderBoot(boot: BootTimings): void {
  bootEl.innerHTML = `
    <table>
      <tr><th>From cache</th><td>${boot.fromCache ? "yes (warm)" : "no (cold)"}</td></tr>
      <tr><th>Manifest</th><td>${fmt(boot.manifestMs)}</td></tr>
      <tr><th>Download</th><td>${fmt(boot.downloadMs)} (${fmtBytes(boot.compressedBytes)})</td></tr>
      <tr><th>Decompress</th><td>${fmt(boot.decompressMs)} → ${fmtBytes(boot.decompressedBytes)}</td></tr>
      <tr><th>Write OPFS</th><td>${fmt(boot.writeOpfsMs)}</td></tr>
      <tr><th>Open SQLite</th><td>${fmt(boot.openMs)}</td></tr>
      <tr><th><strong>Total boot</strong></th><td><strong>${fmt(boot.totalMs)}</strong></td></tr>
    </table>
  `;
}

function renderQueries(report: BenchmarkReport): void {
  const rows = report.queries
    .map(
      (q) => `
      <tr>
        <td>${q.label}</td>
        <td>${q.runs}</td>
        <td>${q.rows}</td>
        <td>${fmt(q.p50Ms)}</td>
        <td>${fmt(q.p95Ms)}</td>
        <td>${fmt(q.p99Ms)}</td>
        <td>${fmt(q.maxMs)}</td>
      </tr>`,
    )
    .join("");
  queriesEl.innerHTML = `
    <table>
      <thead>
        <tr><th>Query</th><th>Runs</th><th>Rows</th><th>p50</th><th>p95</th><th>p99</th><th>max</th></tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
    <p class="ua">${report.userAgent}</p>
  `;
}

function ensureWorker(): Worker {
  if (!worker) {
    worker = new Worker(new URL("./worker.ts", import.meta.url), { type: "module" });
    worker.onmessage = (event: MessageEvent<WorkerResponse>) => {
      const message = event.data;
      if (message.type === "status") {
        statusEl.textContent = message.status + (message.detail ? `: ${message.detail}` : "");
        log(`status → ${message.status}${message.detail ? ` (${message.detail})` : ""}`);
      } else if (message.type === "ready") {
        renderBoot(message.boot);
        log(`ready in ${fmt(message.boot.totalMs)} (${message.boot.fromCache ? "warm" : "cold"})`);
        runBenchmark();
      } else if (message.type === "benchmarkResult") {
        renderQueries(message.report);
        log("benchmark complete");
        setBusy(false);
      } else if (message.type === "error") {
        statusEl.textContent = `failed: ${message.error.code}`;
        log(`ERROR [${message.error.code}] ${message.error.message}`);
        setBusy(false);
      }
    };
    worker.onerror = (event) => {
      log(`worker error: ${event.message}`);
      setBusy(false);
    };
  }
  return worker;
}

function setBusy(busy: boolean): void {
  runColdBtn.disabled = busy;
  runWarmBtn.disabled = busy;
}

function runBenchmark(): void {
  ensureWorker().postMessage({ type: "benchmark", id: ++requestId, runsPerQuery: 25 });
}

function init(reset: boolean): void {
  setBusy(true);
  bootEl.innerHTML = "";
  queriesEl.innerHTML = "";
  ensureWorker().postMessage({ type: "init", id: ++requestId, manifestUrl: MANIFEST_URL, reset });
}

runColdBtn.addEventListener("click", () => init(true));
runWarmBtn.addEventListener("click", () => init(false));

log("harness ready — click a button to run");
