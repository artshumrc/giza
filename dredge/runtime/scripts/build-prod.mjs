// Production build for the standalone Dredge browser library.
//
// Emits self-contained, framework-free assets into dist-prod/search/:
//   dredge-worker.js   – the search Web Worker (+ co-located sqlite/brotli wasm
//                        and the nested OPFS proxy worker chunk)
//   dredge-client.js   – ESM bundle exporting DredgeSearchClient
//
// A relative base ("./") makes the worker's `new URL(asset, import.meta.url)`
// lookups resolve next to wherever the worker is served, so the whole folder
// can be dropped under any path (giza serves it at /search/).

import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { build } from "vite";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..");

/**
 * Build the Dredge browser library (worker + client) into `outDir`.
 * @param {string} [outDir] absolute output directory (defaults to dist-prod/search)
 */
export async function buildLibrary(outDir = resolve(root, "dist-prod/search")) {
  // 1. Worker bundle (side-effect entry; brings in sqlite + brotli wasm assets).
  await build({
    root,
    base: "./",
    configFile: false,
    publicDir: false,
    logLevel: "warn",
    build: {
      outDir,
      emptyOutDir: true,
      target: "es2022",
      minify: true,
      rollupOptions: {
        input: resolve(root, "src/search-worker.ts"),
        output: {
          format: "es",
          entryFileNames: "dredge-worker.js",
          chunkFileNames: "[name]-[hash].js",
          assetFileNames: "[name]-[hash][extname]",
        },
      },
    },
    worker: { format: "es" },
  });

  // 2. Client bundle (library entry; exports DredgeSearchClient). lib mode keeps
  //    the exports intact and never pulls in the worker/sqlite code.
  await build({
    root,
    base: "./",
    configFile: false,
    publicDir: false,
    logLevel: "warn",
    build: {
      outDir,
      emptyOutDir: false,
      target: "es2022",
      minify: true,
      lib: {
        entry: resolve(root, "src/client.ts"),
        formats: ["es"],
        fileName: () => "dredge-client.js",
      },
    },
  });

  return outDir;
}

// Run directly: build into the default dist-prod/search location.
if (import.meta.url === `file://${process.argv[1]}`) {
  const out = await buildLibrary();
  console.log(`dredge library built into ${out}`);
}
