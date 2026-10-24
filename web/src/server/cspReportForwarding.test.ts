import { describe, expect, it } from "vitest";

import { createKeyedWindowLimiter, reportClientKey, sentryCspReport, sentrySecurityUrl } from "./cspReportForwarding";
import type { CspViolation } from "./cspReports";

const VIOLATION: CspViolation = {
  documentPath: "/b/business_1/overview",
  directive: "style-src-attr",
  blocked: "inline",
  sourceFile: null,
  line: 4,
  column: null,
  disposition: "enforce",
};

describe("sentrySecurityUrl", () => {
  it("points at the security endpoint of the DSN's project with its key, environment and release", () => {
    const url = new URL(
      sentrySecurityUrl({ SENTRY_DSN: "https://public0000@o1.ingest.sentry.io/4500", NODE_ENV: "production", APP_RELEASE: "abc123" }) ?? "",
    );

    expect(`${url.origin}${url.pathname}`).toBe("https://o1.ingest.sentry.io/api/4500/security/");
    expect(url.searchParams.get("sentry_key")).toBe("public0000");
    expect(url.searchParams.get("sentry_environment")).toBe("production");
    expect(url.searchParams.get("sentry_release")).toBe("abc123");
  });

  it("is off without a usable DSN", () => {
    expect(sentrySecurityUrl({})).toBeNull();
    expect(sentrySecurityUrl({ SENTRY_DSN: "not a url" })).toBeNull();
    expect(sentrySecurityUrl({ SENTRY_DSN: "https://o1.ingest.sentry.io/4500" })).toBeNull();
    expect(sentrySecurityUrl({ SENTRY_DSN: "ftp://key@o1.ingest.sentry.io/4500" })).toBeNull();
    expect(sentrySecurityUrl({ SENTRY_DSN: "https://key@o1.ingest.sentry.io/project" })).toBeNull();
  });
});

describe("sentryCspReport", () => {
  it("writes the cleaned violation in the report-uri form", () => {
    expect(JSON.parse(sentryCspReport(VIOLATION, "https://cabinet.example.com"))).toEqual({
      "csp-report": {
        "document-uri": "https://cabinet.example.com/b/business_1/overview",
        "effective-directive": "style-src-attr",
        "violated-directive": "style-src-attr",
        "blocked-uri": "inline",
        "line-number": 4,
        disposition: "enforce",
      },
    });
    const full = JSON.parse(sentryCspReport({ ...VIOLATION, sourceFile: "https://cabinet.example.com/app.js", column: 9 }, "https://x"));
    expect(full["csp-report"]).toMatchObject({ "source-file": "https://cabinet.example.com/app.js", "column-number": 9 });
  });
});

describe("reportClientKey", () => {
  it("counts a report against the address the trusted proxies saw, else against one shared key", () => {
    const headers = new Headers({ "x-forwarded-for": "198.51.100.7, 203.0.113.9, 10.0.0.2" });

    expect(reportClientKey(headers, { TRUSTED_PROXY_HOPS: "2" })).toBe("203.0.113.9");
    expect(reportClientKey(headers, { TRUSTED_PROXY_HOPS: "0" })).toBe("direct");
    expect(reportClientKey(new Headers(), { TRUSTED_PROXY_HOPS: "1" })).toBe("direct");
  });
});

describe("createKeyedWindowLimiter", () => {
  it("allows a few per key and window, then opens a new window", () => {
    let now = 0;
    const tryAcquire = createKeyedWindowLimiter(2, 1_000, 10, () => now);

    expect([tryAcquire("a"), tryAcquire("a"), tryAcquire("a"), tryAcquire("b")]).toEqual([true, true, false, true]);
    now = 1_000;
    expect(tryAcquire("a")).toBe(true);
  });

  it("keeps a bounded number of keys: expired windows go first, then the oldest", () => {
    let now = 0;
    const tryAcquire = createKeyedWindowLimiter(1, 1_000, 2, () => now);

    expect(tryAcquire("a")).toBe(true);
    now = 500;
    expect(tryAcquire("b")).toBe(true);
    now = 1_200;
    // "a" has expired: it makes room, and "b" keeps its window.
    expect(tryAcquire("c")).toBe(true);
    expect(tryAcquire("b")).toBe(false);
    // Full of live windows: the oldest ("b") is forgotten for "d".
    expect(tryAcquire("d")).toBe(true);
    expect(tryAcquire("b")).toBe(true);
  });
});
