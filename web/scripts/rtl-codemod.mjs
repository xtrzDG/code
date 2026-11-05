/**
 * Physical-direction Tailwind classes -> logical ones, in place:
 *
 *   node scripts/rtl-codemod.mjs            # rewrite every file under src/
 *   node scripts/rtl-codemod.mjs --check    # list them, exit 1 if any
 *   node scripts/rtl-codemod.mjs src/components/ui   # only these paths
 *
 * The rules (ml -> ms, left -> start, text-left -> text-start, …) live in
 * src/lib/rtl/logicalClasses.ts, which the policy test uses too; Node reads
 * that TypeScript file by stripping its types (Node 22.12+).
 */

import { readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { findPhysicalClasses, toLogicalClasses } from "../src/lib/rtl/logicalClasses.ts";

const WEB_DIRECTORY = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const SOURCE = /\.(ts|tsx)$/;
/** The rules themselves and their tests name physical classes on purpose. */
const RULES_DIRECTORY = path.join(WEB_DIRECTORY, "src", "lib", "rtl");

function sourceFiles(target) {
  const stats = statSync(target);
  if (target.startsWith(RULES_DIRECTORY)) {
    return [];
  }
  if (stats.isFile()) {
    return SOURCE.test(target) ? [target] : [];
  }
  return readdirSync(target, { withFileTypes: true }).flatMap((entry) =>
    entry.name === "node_modules" || entry.name.startsWith(".") ? [] : sourceFiles(path.join(target, entry.name)),
  );
}

const args = process.argv.slice(2);
const check = args.includes("--check");
const targets = args.filter((arg) => arg !== "--check");
const files = (targets.length > 0 ? targets : ["src"]).flatMap((target) => sourceFiles(path.resolve(WEB_DIRECTORY, target)));

let total = 0;
for (const file of files) {
  const source = readFileSync(file, "utf8");
  const found = findPhysicalClasses(source);
  if (found.length === 0) {
    continue;
  }
  total += found.length;
  const name = path.relative(WEB_DIRECTORY, file);
  if (check) {
    for (const entry of found) {
      process.stdout.write(`${name}:${entry.line}  ${entry.found} -> ${entry.logical}\n`);
    }
  } else {
    writeFileSync(file, toLogicalClasses(source));
    process.stdout.write(`${name}: ${found.length}\n`);
  }
}

process.stdout.write(check ? `${total} physical-direction classes\n` : `${total} classes made logical\n`);
if (check && total > 0) {
  process.exitCode = 1;
}
