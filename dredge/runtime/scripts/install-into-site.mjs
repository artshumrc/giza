// Build the Dredge browser library and install its assets into a static site's
// /search/ directory (alongside the compiled database + manifest).
//
// Usage: node scripts/install-into-site.mjs --out <static-site-dir>
//
// Copies dredge-worker.js, dredge-client.js, the wasm payloads and chunk assets
// into <static-site-dir>/search/. The compiled DB + search-manifest.json are
// produced separately by `dredge compile` into the same folder.

import { cp, mkdir, readdir } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { buildLibrary } from "./build-prod.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const buildDir = resolve(here, "..", "dist-prod", "search");

function parseOut(argv) {
  const index = argv.indexOf("--out");
  if (index === -1 || !argv[index + 1]) {
    throw new Error("usage: install-into-site.mjs --out <static-site-dir>");
  }
  return resolve(argv[index + 1]);
}

const siteDir = parseOut(process.argv.slice(2));
const searchDir = join(siteDir, "search");

await buildLibrary(buildDir);
await mkdir(searchDir, { recursive: true });

for (const entry of await readdir(buildDir, { withFileTypes: true })) {
  await cp(join(buildDir, entry.name), join(searchDir, entry.name), { recursive: true });
}

console.log(`installed dredge library assets into ${searchDir}`);
