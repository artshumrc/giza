import { defineConfig } from "vite";

// The OPFS SyncAccessHandle pool VFS used by the worker does NOT require
// cross-origin isolation (no SharedArrayBuffer), which keeps hosting simple.
// We still set the headers in dev so the harness matches a COOP/COEP host if
// one is used later, and they are harmless for the SAH pool path.
export default defineConfig({
  server: {
    headers: {
      "Cross-Origin-Opener-Policy": "same-origin",
      "Cross-Origin-Embedder-Policy": "require-corp",
    },
  },
  preview: {
    headers: {
      "Cross-Origin-Opener-Policy": "same-origin",
      "Cross-Origin-Embedder-Policy": "require-corp",
    },
  },
  optimizeDeps: {
    // sqlite-wasm ships its own worker/wasm; let Vite serve it untransformed.
    exclude: ["@sqlite.org/sqlite-wasm"],
  },
  worker: {
    format: "es",
  },
});
