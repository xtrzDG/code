/**
 * The inventory of the payment pages' scripts (PAY-02,
 * scripts/payment-page-scripts.mjs): which scripts a page loads according to
 * the build, the reviewed inventory's shape, and the differences the weekly
 * integrity check reports (.github/workflows/payment-page-integrity.yml).
 */

import { readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import { PAYMENT_PAGE_ROUTES } from "@/lib/paymentPages";

import {
  PAYMENT_PAGES,
  differences,
  entryScripts,
  loadedScripts,
  parseClientManifest,
  parseInventory,
  renderReport,
  routeManifestPaths,
  type ScriptInventory,
} from "../../scripts/payment-page-scripts.mjs";

const BILLING = "/b/[businessId]/settings/billing";
const CHAT = "/c/[slug]";
const hash = (letter: string): string => `sha384-${letter.repeat(64)}`;

function inventory(billing: { path: string; integrity: string }[], chat = billing): ScriptInventory {
  return { pages: { [BILLING]: billing, [CHAT]: chat } };
}

describe("the scripts a payment page loads", () => {
  it("are the payment pages the cabinet marks, and the hosted chat page", () => {
    expect([...PAYMENT_PAGES].sort()).toEqual([...PAYMENT_PAGE_ROUTES, CHAT].sort());
    expect(routeManifestPaths(BILLING)).toEqual({
      buildManifest: "server/app/b/[businessId]/settings/billing/page/build-manifest.json",
      clientManifest: "server/app/b/[businessId]/settings/billing/page_client-reference-manifest.js",
    });
  });

  it("come from the build manifest and the client manifest of the route, once each", () => {
    const text = [
      "globalThis.__RSC_MANIFEST = globalThis.__RSC_MANIFEST || {};",
      `globalThis.__RSC_MANIFEST["${BILLING}/page"] = ${JSON.stringify({
        clientModules: { a: { chunks: ["/_next/static/chunks/c.js"] }, b: { chunks: [] } },
        entryJSFiles: { layout: ["static/chunks/b.js"], page: ["static/chunks/b.js", "static/chunks/d.js"] },
        entryCSSFiles: { layout: ["static/chunks/e.css"] },
      })};`,
    ].join("\n");

    const entries = entryScripts(
      { polyfillFiles: ["static/chunks/p.js"], rootMainFiles: ["static/chunks/a.js", "static/chunks/b.js"] },
      parseClientManifest(text, BILLING),
    );

    expect(entries).toEqual(["static/chunks/a.js", "static/chunks/b.js", "static/chunks/c.js", "static/chunks/d.js", "static/chunks/p.js"]);
  });

  it("refuse a client manifest that names another page: the build's format changed", () => {
    expect(() => parseClientManifest('globalThis.__RSC_MANIFEST["/other/page"] = {};', BILLING)).toThrow(/no client manifest/);
  });

  it("include every chunk a loaded chunk names, lazily loaded ones too", () => {
    const files: Record<string, string> = {
      "static/chunks/a.js": 'load("static/chunks/lazy.js");load("static/chunks/b.js")',
      "static/chunks/b.js": 'back("static/chunks/a.js")',
      "static/chunks/lazy.js": "done()",
    };

    expect(loadedScripts(["static/chunks/a.js"], (file) => files[file] ?? "")).toEqual([
      "static/chunks/a.js",
      "static/chunks/b.js",
      "static/chunks/lazy.js",
    ]);
  });
});

describe("the reviewed inventory", () => {
  it("is the committed one, and lists every payment page with first-party scripts only", () => {
    const committed = JSON.parse(readFileSync(path.resolve(__dirname, "../../payment-page-scripts.json"), "utf8")) as unknown;

    const parsed = parseInventory(committed);
    for (const route of PAYMENT_PAGES) {
      expect(parsed.pages[route]?.every((script) => script.path.startsWith("static/chunks/")), route).toBe(true);
    }
  });

  it("refuses a file it cannot trust", () => {
    const script = { path: "static/chunks/a.js", integrity: hash("A") };
    expect(() => parseInventory(null)).toThrow(/`pages` is missing/);
    expect(() => parseInventory({ pages: { [BILLING]: [script] } })).toThrow(/must be exactly/);
    expect(() => parseInventory(inventory([]))).toThrow(/lists no script/);
    expect(() => parseInventory(inventory([{ path: "https://cdn.example/a.js", integrity: hash("A") }]))).toThrow(
      /build path/,
    );
    expect(() => parseInventory(inventory([{ path: "static/chunks/a.js", integrity: "sha256-abc" }]))).toThrow(/sha384/);
    expect(parseInventory(inventory([script]))).toEqual(inventory([script]));
  });
});

describe("the differences", () => {
  const reviewed = inventory([
    { path: "static/chunks/a.js", integrity: hash("A") },
    { path: "static/chunks/b.js", integrity: hash("B") },
  ]);

  it("are none when every script is the reviewed one", () => {
    expect(differences(reviewed, reviewed)).toEqual([]);
    expect(renderReport([], "the scripts of this build")).toContain("Every script of the payment pages is the reviewed one.");
  });

  it("name each script added, removed, changed or not served, page by page", () => {
    const found: ScriptInventory = {
      pages: {
        [BILLING]: [
          { path: "static/chunks/a.js", integrity: hash("C") },
          { path: "static/chunks/new.js", integrity: hash("D") },
        ],
        [CHAT]: [
          { path: "static/chunks/a.js", status: 404 },
          { path: "static/chunks/b.js", integrity: hash("B") },
        ],
      },
    };

    const changes = differences(reviewed, found);

    expect(changes).toEqual([
      { route: BILLING, path: "static/chunks/a.js", kind: "changed", detail: `${hash("A")} → ${hash("C")}` },
      { route: BILLING, path: "static/chunks/new.js", kind: "added", detail: hash("D") },
      { route: BILLING, path: "static/chunks/b.js", kind: "removed", detail: hash("B") },
      { route: CHAT, path: "static/chunks/a.js", kind: "unavailable", detail: "HTTP 404" },
    ]);
    const report = renderReport(changes, "the files https://app.example.com serves");
    expect(report).toContain("**4 difference(s).**");
    expect(report).toContain("| `/c/[slug]` | `static/chunks/a.js` | unavailable | HTTP 404 |");
    expect(report).toContain("Compared: the files https://app.example.com serves against web/payment-page-scripts.json.");
  });
});
