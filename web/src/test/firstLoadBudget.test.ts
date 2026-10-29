import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { overBudget, parseBudget, type FirstLoadBudget } from "../../scripts/first-load-budget.mjs";

const KB = 1024;
const BUDGET: FirstLoadBudget = { pages: { "/en": 192, "/login": 316 }, lazy3dChunk: 244 };
const CHUNK = { name: "three.js", gzip: 241 * KB };

describe("the first-load budget", () => {
  it("passes pages and the 3D chunk within their kilobytes, the limit included", () => {
    const measured = {
      pages: [
        { page: "/en", gzip: 192 * KB },
        { page: "/login", gzip: 300 * KB },
      ],
      lazyChunks: [CHUNK],
    };
    expect(overBudget(BUDGET, measured)).toEqual([]);
  });

  it("names a page over its budget and a page that was not measured", () => {
    const measured = { pages: [{ page: "/en", gzip: 192 * KB + 1 }], lazyChunks: [CHUNK] };
    expect(overBudget(BUDGET, measured)).toEqual(["/en: 192.0 KB gzip, over its budget of 192 KB", "/login: not measured"]);
  });

  it("wants exactly one lazy 3D chunk, within its budget", () => {
    const pages = [
      { page: "/en", gzip: 180 * KB },
      { page: "/login", gzip: 300 * KB },
    ];
    expect(overBudget(BUDGET, { pages, lazyChunks: [] })).toEqual([
      "no lazy 3D chunk in the build: three.js must stay behind the scenes' import()",
    ]);
    const twice = overBudget(BUDGET, { pages, lazyChunks: [CHUNK, { name: "copy.js", gzip: 10 * KB }] });
    expect(twice).toEqual(["2 chunks carry three.js (three.js, copy.js): one is shared by every scene"]);
    const heavy = overBudget(BUDGET, { pages, lazyChunks: [{ name: "three.js", gzip: 250 * KB }] });
    expect(heavy).toEqual(["lazy 3D chunk three.js: 250.0 KB gzip, over its budget of 244 KB"]);
  });

  it("refuses a budget file it cannot trust", () => {
    expect(() => parseBudget(null)).toThrow(/not an object/);
    expect(() => parseBudget({ pages: {}, lazy3dChunk: 1 })).toThrow(/at least one page/);
    expect(() => parseBudget({ pages: { en: 1 }, lazy3dChunk: 1 })).toThrow(/must start with \//);
    expect(() => parseBudget({ pages: { "/en": 0 }, lazy3dChunk: 1 })).toThrow(/positive/);
    expect(() => parseBudget({ pages: { "/en": 1 }, lazy3dChunk: Number.NaN })).toThrow(/lazy3dChunk/);
  });

  it("is the committed file, covering the landing, a legal page, the cabinet and the offline page", () => {
    const file = fileURLToPath(new URL("../../first-load-budget.json", import.meta.url));
    const budget = parseBudget(JSON.parse(readFileSync(file, "utf8")));
    expect(Object.keys(budget.pages)).toEqual(expect.arrayContaining(["/en", "/ka/terms", "/login", "/offline"]));
  });
});
