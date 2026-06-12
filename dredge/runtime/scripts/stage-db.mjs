// Copies a compiler output directory (manifest + .db.br) into the harness's
// served public/search directory so the Vite dev server can serve them.
//
// Usage:
//   node scripts/stage-db.mjs <compiler-output-dir>
//   node scripts/stage-db.mjs ../.stress/site150k/search

import { cp, mkdir, readdir, rm, stat } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const target = resolve(here, "..", "public", "search");

const sourceArg = process.argv[2] ?? resolve(here, "..", "..", ".stress", "site150k", "search");
const source = resolve(process.cwd(), sourceArg);

async function main() {
  const info = await stat(source).catch(() => null);
  if (!info?.isDirectory()) {
    console.error(`source directory not found: ${source}`);
    process.exit(1);
  }

  const entries = await readdir(source);
  const manifest = entries.find((name) => name === "search-manifest.json");
  const compressed = entries.filter((name) => name.endsWith(".db.br"));
  if (!manifest || compressed.length === 0) {
    console.error(`source is missing search-manifest.json or *.db.br: ${source}`);
    process.exit(1);
  }

  await rm(target, { recursive: true, force: true });
  await mkdir(target, { recursive: true });

  await cp(join(source, manifest), join(target, manifest));
  for (const name of compressed) {
    await cp(join(source, name), join(target, name));
  }

  console.log(`staged ${manifest} + ${compressed.join(", ")} into ${target}`);
}

main();
