/**
 * The cabinet reads right to left in Hebrew: no class in src/ may name a
 * side of the screen (ml-2, left-0, text-left, rounded-r-lg). Use the
 * logical twin (ms-2, start-0, text-start, rounded-e-lg), which the browser
 * mirrors by itself; `node scripts/rtl-codemod.mjs` rewrites a file. A class
 * that must stay physical says so with the rtl: or ltr: variant.
 */

import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import { findPhysicalClasses } from "./logicalClasses";

const SOURCE_DIRECTORY = path.resolve(__dirname, "../..");
const RULES_DIRECTORY = path.resolve(__dirname);

function sourceFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      return full === RULES_DIRECTORY ? [] : sourceFiles(full);
    }
    return /\.(ts|tsx)$/.test(entry.name) ? [full] : [];
  });
}

describe("the cabinet's classes", () => {
  it("name the start and end of the text, never a side of the screen", () => {
    const offending = sourceFiles(SOURCE_DIRECTORY).flatMap((file) =>
      findPhysicalClasses(readFileSync(file, "utf8")).map(
        (entry) => `${path.relative(SOURCE_DIRECTORY, file)}:${entry.line} ${entry.found} -> ${entry.logical}`,
      ),
    );
    expect(offending).toEqual([]);
  });
});
