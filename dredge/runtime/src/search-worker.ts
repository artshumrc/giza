/// <reference lib="webworker" />

import { boot, closeDatabase, getExec, toDredgeError } from "./db";
import { introspectSchema, search } from "./search";
import type { DredgeSearchRequest, DredgeSearchResponse, SchemaInfo } from "./search";
import type { DredgeError, DredgeStatus } from "./protocol";

type WorkerRequest =
  | { type: "init"; id: number; manifestUrl: string; reset?: boolean }
  | { type: "search"; id: number; request: DredgeSearchRequest }
  | { type: "destroy"; id: number };

type WorkerResponse =
  | { type: "status"; status: DredgeStatus; detail?: string }
  | { type: "ready"; id: number }
  | { type: "searchResult"; id: number; response: DredgeSearchResponse }
  | { type: "error"; id?: number; error: DredgeError };

let schema: SchemaInfo | undefined;

function post(message: WorkerResponse): void {
  (self as DedicatedWorkerGlobalScope).postMessage(message);
}

function status(value: DredgeStatus, detail?: string): void {
  post({ type: "status", status: value, detail });
}

self.onmessage = async (event: MessageEvent<WorkerRequest>) => {
  const message = event.data;
  try {
    if (message.type === "init") {
      await boot(message.manifestUrl, message.reset ?? false, status);
      schema = introspectSchema(getExec());
      post({ type: "ready", id: message.id });
      return;
    }
    if (message.type === "search") {
      const exec = getExec();
      if (!schema) {
        schema = introspectSchema(exec);
      }
      const response = search(exec, schema, message.request);
      post({ type: "searchResult", id: message.id, response });
      return;
    }
    if (message.type === "destroy") {
      closeDatabase();
      schema = undefined;
      return;
    }
  } catch (error) {
    status("failed");
    post({ type: "error", id: (message as { id?: number }).id, error: toDredgeError(error) });
  }
};
