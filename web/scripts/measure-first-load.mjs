#!/usr/bin/env node
/**
 * First-load JavaScript of pages of the last `next build`, gzipped, as the
 * browser downloads it: starts `next start`, reads each page's HTML, sums the
 * <script src> files it loads (gzip level 6, like a web server) and lists the
 * lazy chunks that hold three.js (the landing's 3D scene, loaded only after
 * the page is interactive).
 *
 *   npm run build && npm run measure:first-load            # "/" and "/login"
 *   npm run measure:first-load -- / /businesses           # other pages
 *
 * The API does not have to run: the landing renders without the catalog.
 */

import { spawn } from "node:child_process";
import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { gzipSync } from "node:zlib";

const WEB_DIRECTORY = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const PORT = Number(process.env.MEASURE_PORT ?? 3899);
const ORIGIN = `http://127.0.0.1:${PORT}`;
const pages = process.argv.slice(2).length > 0 ? process.argv.slice(2) : ["/", "/login"];

const kilobytes = (bytes) => `${(bytes / 1024).toFixed(1)} KB`;
const gzipSize = (buffer) => gzipSync(buffer, { level: 6 }).length;

async function waitForServer(deadline) {
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${ORIGIN}/login`, { redirect: "manual" });
      if (response.status < 500) {
        return;
      }
    } catch {
      // Not listening yet.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`next start did not answer on ${ORIGIN}`);
}

async function measurePage(page) {
  const html = await (await fetch(`${ORIGIN}${page}`, { redirect: "manual" })).text();
  // `noModule` polyfills are skipped by every browser the cabinet supports.
  const tags = [...html.matchAll(/<script[^>]*\ssrc="([^"]+)"[^>]*>/g)].filter((match) => !/\snoModule/i.test(match[0]));
  const sources = [...new Set(tags.map((match) => match[1]))];
  let raw = 0;
  let gzip = 0;
  for (const source of sources) {
    const body = Buffer.from(await (await fetch(new URL(source, ORIGIN))).arrayBuffer());
    raw += body.length;
    gzip += gzipSize(body);
  }
  return { page, scripts: sources.length, raw, gzip };
}

/** Chunks of the build that contain three.js: loaded later, on demand. */
function lazyThreeChunks() {
  const directory = path.join(WEB_DIRECTORY, ".next", "static", "chunks");
  const files = [];
  const walk = (folder) => {
    for (const name of readdirSync(folder)) {
      const file = path.join(folder, name);
      if (statSync(file).isDirectory()) {
        walk(file);
      } else if (name.endsWith(".js")) {
        const body = readFileSync(file);
        if (body.includes("WebGLRenderer")) {
          files.push({ name: path.relative(directory, file), raw: body.length, gzip: gzipSize(body) });
        }
      }
    }
  };
  walk(directory);
  return files;
}

const server = spawn("npx", ["next", "start", "--port", String(PORT), "--hostname", "127.0.0.1"], {
  cwd: WEB_DIRECTORY,
  env: { ...process.env, BACKEND_URL: process.env.BACKEND_URL ?? "http://127.0.0.1:9", NEXT_TELEMETRY_DISABLED: "1" },
  stdio: "ignore",
  detached: true,
});

try {
  await waitForServer(Date.now() + 60_000);
  for (const page of pages) {
    const result = await measurePage(page);
    process.stdout.write(`${result.page}: ${result.scripts} scripts, ${kilobytes(result.raw)} raw, ${kilobytes(result.gzip)} gzip\n`);
  }
  for (const chunk of lazyThreeChunks()) {
    process.stdout.write(`lazy 3D chunk ${chunk.name}: ${kilobytes(chunk.raw)} raw, ${kilobytes(chunk.gzip)} gzip\n`);
  }
} finally {
  process.kill(-server.pid, "SIGTERM");
}
