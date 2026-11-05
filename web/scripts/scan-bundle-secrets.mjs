/**
 * Fails when the cabinet's build carries a secret (WEB-05; rules in
 * bundle-secrets.mjs). CI runs it right after `next build` in the job
 * "web-build":
 *
 *   node scripts/scan-bundle-secrets.mjs --build .next \
 *     --env-example .env.example --env-example ../.env.example
 *
 * Every file of `<build>/static` (what browsers download) and
 * `<build>/server` (the server's bundles and prerendered pages) is read;
 * images, fonts and media are skipped. The values of secret variables are
 * looked for in what browsers receive: `static` and the prerendered pages. Hits are printed masked, as GitHub
 * annotations. Exit codes: 0 nothing found, 1 a secret found, 2 no build
 * to scan (a scan of nothing proves nothing).
 */

import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { parseArgs } from "node:util";

import { documentedVariables, findSecrets, isBrowserFile, secretValues } from "./bundle-secrets.mjs";

const BINARY_FILE = /\.(?:png|jpe?g|gif|webp|avif|ico|woff2?|ttf|otf|eot|mp3|mp4|webm|wasm|glb|gltf|bin)$/i;
const SCANNED_DIRECTORIES = ["static", "server"];

function filesUnder(directory) {
  const files = [];
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) {
      files.push(...filesUnder(path));
    } else if (entry.isFile() && !BINARY_FILE.test(entry.name)) {
      files.push(path);
    }
  }
  return files;
}

const { values: options } = parseArgs({
  options: {
    build: { type: "string", default: ".next" },
    "env-example": { type: "string", multiple: true, default: [] },
  },
});

const missing = SCANNED_DIRECTORIES.filter((name) => !existsSync(join(options.build, name)));
if (missing.length > 0) {
  console.error(`No build to scan: ${missing.map((name) => join(options.build, name)).join(", ")} missing. Run next build first.`);
  process.exit(2);
}

const names = options["env-example"].flatMap((path) => documentedVariables(readFileSync(path, "utf8")));
const values = secretValues(names, process.env);
let scanned = 0;
const hits = [];
for (const directory of SCANNED_DIRECTORIES) {
  for (const path of filesUnder(join(options.build, directory))) {
    if (statSync(path).size === 0) {
      continue;
    }
    scanned += 1;
    const browser = isBrowserFile(relative(options.build, path).split(sep).join("/"));
    hits.push(...findSecrets(relative(".", path), readFileSync(path, "latin1"), { values, isBrowserFile: browser }));
  }
}

for (const hit of hits) {
  console.error(`::error file=${hit.file}::${hit.rule}: ${hit.excerpt}`);
}
const searched = values.length > 0 ? ` and the values of ${values.map(({ name }) => name).join(", ")}` : "";
if (hits.length > 0) {
  console.error(`${hits.length} secret(s) in the build (${scanned} files): remove them from the code; rotate any real one.`);
  process.exit(1);
}
console.warn(`No secret in ${scanned} files of the build (key shapes${searched}).`);
