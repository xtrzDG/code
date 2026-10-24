import { describe, expect, it } from "vitest";

import { isCspReportContentType, parseCspReports } from "./cspReports";

function legacy(report: Record<string, unknown>): string {
  return JSON.stringify({ "csp-report": report });
}

describe("parseCspReports", () => {
  it("reads a report-uri report without its query, sample or referrer", () => {
    const parsed = parseCspReports(
      legacy({
        "document-uri": "https://cabinet.example.com/b/business_1/overview?view=all#top",
        referrer: "https://cabinet.example.com/login?email=owner@example.com",
        "violated-directive": "style-src-attr 'self' 'nonce-abc'",
        "effective-directive": "style-src-attr",
        "blocked-uri": "inline",
        "script-sample": "color: red",
        "source-file": "https://cabinet.example.com/_next/static/chunks/app.js?v=1",
        "line-number": 12,
        "column-number": 40,
        disposition: "enforce",
      }),
    );

    expect(parsed).toEqual([
      {
        documentPath: "/b/business_1/overview",
        directive: "style-src-attr",
        blocked: "inline",
        sourceFile: "https://cabinet.example.com/_next/static/chunks/app.js",
        line: 12,
        column: 40,
        disposition: "enforce",
      },
    ]);
  });

  it("names the directive from an old violated-directive and keeps unknown parts empty", () => {
    const [violation] =
      parseCspReports(
        legacy({ "document-uri": "https://cabinet.example.com/login", "violated-directive": "script-src-elem 'self'", disposition: "report" }),
      ) ?? [];

    expect(violation).toMatchObject({ directive: "script-src-elem", blocked: "unknown", sourceFile: null, line: null, column: null, disposition: "report" });
  });

  it("hides the key of a customer's booking page", () => {
    const [violation] =
      parseCspReports(
        legacy({
          "document-uri": "https://cabinet.example.com/r/test-token-0000",
          "effective-directive": "img-src",
          "blocked-uri": "https://cabinet.example.com/r/test-token-0000/map.png",
        }),
      ) ?? [];

    expect(violation?.documentPath).not.toContain("test-token-0000");
    expect(violation?.blocked).not.toContain("test-token-0000");
  });

  it("keeps only the origin and path of what was blocked, and the scheme of anything else", () => {
    const blockedOf = (blocked: string) =>
      parseCspReports(legacy({ "document-uri": "https://cabinet.example.com/", "effective-directive": "connect-src", "blocked-uri": blocked }))?.[0]
        ?.blocked;

    expect(blockedOf("https://user:secret@tracker.example/collect?id=1")).toBe("https://tracker.example/collect");
    expect(blockedOf("data:text/html;base64,AAAA")).toBe("data:");
    expect(blockedOf("trusted-types-sink")).toBe("trusted-types-sink");
    expect(blockedOf("not a url at all")).toBe("unknown");
  });

  it("reads a Reporting API batch, skips what is not a CSP violation and caps the batch", () => {
    const one = {
      type: "csp-violation",
      url: "https://cabinet.example.com/help",
      body: { effectiveDirective: "require-trusted-types-for", blockedURL: "trusted-types-sink", lineNumber: 3, columnNumber: -1 },
    };
    const batch = [{ type: "deprecation", body: {} }, { type: "csp-violation", body: "nope" }, ...Array.from({ length: 30 }, () => one)];

    const parsed = parseCspReports(JSON.stringify(batch)) ?? [];

    expect(parsed).toHaveLength(10);
    expect(parsed[0]).toMatchObject({ documentPath: "/help", directive: "require-trusted-types-for", line: 3, column: null });
  });

  it("refuses what is not a report", () => {
    expect(parseCspReports("not json")).toBeNull();
    expect(parseCspReports("42")).toBeNull();
    expect(parseCspReports(JSON.stringify({ other: true }))).toBeNull();
    expect(parseCspReports(legacy({ "document-uri": "nowhere", "effective-directive": "img-src" }))).toBeNull();
    expect(parseCspReports(legacy({ "document-uri": "https://cabinet.example.com/", "effective-directive": "Not A Directive" }))).toBeNull();
  });
});

describe("isCspReportContentType", () => {
  it.each([
    ["application/csp-report", true],
    ["application/reports+json; charset=utf-8", true],
    ["Application/JSON", true],
    ["text/plain", false],
    [null, false],
  ])("%s → %s", (header, expected) => {
    expect(isCspReportContentType(header)).toBe(expected);
  });
});
