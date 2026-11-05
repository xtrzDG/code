/**
 * Compares the payment pages' scripts with the reviewed inventory
 * (payment-page-scripts.json; rules in payment-page-scripts.mjs). Run every
 * week by .github/workflows/payment-page-integrity.yml, from web/:
 *
 *   # the deployed files, as browsers receive them
 *   node scripts/payment-page-integrity.mjs --origin https://app.example.com
 *   # without production's address: the scripts of a fresh build
 *   node scripts/payment-page-integrity.mjs --build .next --write found.json
 *   # after reviewing a change: the build becomes the inventory
 *   node scripts/payment-page-integrity.mjs --build .next --update
 *
 * `--report <file>` also writes the Markdown report there (the run
 * summary). Exit codes: 0 nothing changed (or the inventory was updated),
 * 1 a script was added, removed, changed or not served, 2 nothing could be
 * compared (no build, no inventory, an unreachable site).
 */

import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { parseArgs } from "node:util";

import {
  PAYMENT_PAGES,
  differences,
  entryScripts,
  loadedScripts,
  parseClientManifest,
  parseInventory,
  renderReport,
  routeManifestPaths,
} from "./payment-page-scripts.mjs";

const FETCH_TIMEOUT_MS = 20_000;

const integrity = (bytes) => `sha384-${createHash("sha384").update(bytes).digest("base64")}`;

function fromBuild(build) {
  const read = (path) => readFileSync(join(build, path), "latin1");
  const pages = {};
  for (const route of PAYMENT_PAGES) {
    const paths = routeManifestPaths(route);
    const entries = entryScripts(
      JSON.parse(read(paths.buildManifest)),
      parseClientManifest(read(paths.clientManifest), route),
    );
    pages[route] = loadedScripts(entries, read).map((path) => ({
      path,
      integrity: integrity(readFileSync(join(build, path))),
    }));
  }
  return { pages };
}

async function fromOrigin(origin, inventory) {
  const served = new Map();
  const pages = {};
  for (const route of PAYMENT_PAGES) {
    pages[route] = [];
    for (const { path } of inventory.pages[route]) {
      if (!served.has(path)) {
        const response = await fetch(new URL(`/_next/${path}`, origin), {
          redirect: "manual",
          signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
        });
        served.set(
          path,
          response.status === 200
            ? { path, integrity: integrity(Buffer.from(await response.arrayBuffer())) }
            : { path, status: response.status },
        );
      }
      pages[route].push(served.get(path));
    }
  }
  return { pages };
}

const { values: options } = parseArgs({
  options: {
    inventory: { type: "string", default: "payment-page-scripts.json" },
    build: { type: "string" },
    origin: { type: "string" },
    write: { type: "string" },
    update: { type: "boolean", default: false },
    report: { type: "string" },
  },
});

try {
  if (Boolean(options.build) === Boolean(options.origin)) {
    throw new Error("give either --build <.next> or --origin <https://…>");
  }
  if (options.update) {
    if (!options.build) {
      throw new Error("--update takes the inventory from a build (--build)");
    }
    writeFileSync(options.inventory, `${JSON.stringify(fromBuild(options.build), null, 2)}\n`);
    console.warn(`${options.inventory} now lists the build's scripts: review the diff before committing it.`);
    process.exit(0);
  }
  const inventory = parseInventory(JSON.parse(readFileSync(options.inventory, "utf8")));
  let found;
  let source;
  if (options.origin) {
    const origin = new URL(options.origin);
    if (origin.protocol !== "https:") {
      throw new Error("--origin must be an https address");
    }
    found = await fromOrigin(origin, inventory);
    source = `the files ${origin.origin} serves`;
  } else {
    found = fromBuild(options.build);
    source = "the scripts of this build";
    if (options.write) {
      writeFileSync(options.write, `${JSON.stringify(found, null, 2)}\n`);
    }
  }
  const changes = differences(inventory, found);
  const report = renderReport(changes, source);
  if (options.report) {
    writeFileSync(options.report, report);
  }
  console.warn(report);
  process.exit(changes.length === 0 ? 0 : 1);
} catch (error) {
  const reason = `Payment page scripts could not be compared: ${error instanceof Error ? error.message : String(error)}`;
  if (options.report) {
    writeFileSync(options.report, `## Payment page scripts\n\n${reason}\n`);
  }
  console.error(reason);
  process.exit(2);
}
