import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const SOURCE_ROOT = fileURLToPath(new URL("../..", import.meta.url));

/** `new Intl.NumberFormat(locale, …)`: a format in a UI language. */
const LOCALE_FORMAT = /new Intl\.(DateTimeFormat|NumberFormat|RelativeTimeFormat|ListFormat|PluralRules)\(\s*([^,)]*)/g;

/** Fixed English formats that read calendar fields or currency digits, never shown as text. */
const FIXED_LOCALE = /^"en(-US|-CA)?"$/;

/**
 * Files the website import work owns (R5-WEBSITE-IMPORT) still format with
 * the browser's Intl: a whole percent and a file size, which read the same
 * in English and Georgian except for the decimal comma. They move to
 * `lib/intl/formatters` when that work lands.
 */
const PENDING = new Set([
  "app/b/[businessId]/assistant/knowledge/import/_components/ImportDraftRow.tsx",
  "lib/knowledge/menuImport.ts",
]);

function sourceFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) {
      return sourceFiles(path);
    }
    return /\.tsx?$/.test(entry.name) && !/\.test\.tsx?$/.test(entry.name) ? [path] : [];
  });
}

describe("formats in a UI language", () => {
  it("go through lib/intl/formatters, which writes Georgian in every browser", () => {
    const offenders: string[] = [];
    for (const path of sourceFiles(SOURCE_ROOT)) {
      const name = relative(SOURCE_ROOT, path).split("\\").join("/");
      if (name.startsWith("lib/intl/") || PENDING.has(name)) {
        continue;
      }
      for (const match of readFileSync(path, "utf8").matchAll(LOCALE_FORMAT)) {
        if (!FIXED_LOCALE.test((match[2] ?? "").trim())) {
          offenders.push(`${name}: ${match[0]}`);
        }
      }
    }
    expect(offenders).toEqual([]);
  });

  it("are still found in the files waiting for their owner", () => {
    for (const name of PENDING) {
      expect(readFileSync(join(SOURCE_ROOT, name), "utf8"), name).toMatch(new RegExp(LOCALE_FORMAT.source));
    }
  });
});
