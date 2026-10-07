import { describe, expect, it } from "vitest";

import { loginPath, safeNextPath, sectionFromPathname, isProtectedPath } from "@/lib/navigation";

import {
  buildBackendPath,
  buildUpstreamHeaders,
  dateFromMicroseconds,
  getBackendUrl,
  isCookieSecure,
  isCrossSiteRequest,
  pickResponseHeaders,
  sanitizeRequestId,
  trustedForwardedFor,
} from "./backend";

describe("BFF path and headers", () => {
  it("forwards only /v1 API paths, encoded", () => {
    expect(buildBackendPath(["v1", "businesses", "business_1", "profile"])).toBe("/v1/businesses/business_1/profile");
    expect(buildBackendPath(["v1", "a b"])).toBe("/v1/a%20b");
    expect(buildBackendPath(["v1", "x/../../docs"])).toBe("/v1/x%2F..%2F..%2Fdocs");
    expect(buildBackendPath(["healthz"])).toBeNull();
    expect(buildBackendPath(["v1"])).toBeNull();
    expect(buildBackendPath(["v1", "..", "docs"])).toBeNull();
  });

  it("adds the token and language, never the browser cookies", () => {
    const incoming = new Headers({
      cookie: "aw_session=secret",
      "content-type": "application/json",
      "accept-language": "de",
      "x-forwarded-for": "203.0.113.77, 198.51.100.9",
      host: "cabinet.example",
    });
    const headers = buildUpstreamHeaders(incoming, { token: "tok", locale: "ka", requestId: "r1" });
    expect(headers.get("authorization")).toBe("Bearer tok");
    expect(headers.get("accept-language")).toBe("ka, en;q=0.5");
    expect(headers.get("content-type")).toBe("application/json");
    // The browser's own X-Forwarded-For could be forged: dropped by default.
    expect(headers.get("x-forwarded-for")).toBeNull();
    expect(headers.get("x-request-id")).toBe("r1");
    expect(headers.get("cookie")).toBeNull();
    expect(headers.get("host")).toBeNull();
  });

  it("forwards only the client address the cabinet's own proxies added", () => {
    const incoming = new Headers({ "x-forwarded-for": "203.0.113.77, 198.51.100.9" });
    expect(trustedForwardedFor(incoming, { TRUSTED_PROXY_HOPS: "1" })).toBe("198.51.100.9");
    expect(trustedForwardedFor(incoming, { TRUSTED_PROXY_HOPS: "2" })).toBe("203.0.113.77, 198.51.100.9");
    expect(trustedForwardedFor(incoming, {})).toBeNull();
    expect(trustedForwardedFor(incoming, { TRUSTED_PROXY_HOPS: "x" })).toBeNull();
    expect(trustedForwardedFor(new Headers(), { TRUSTED_PROXY_HOPS: "1" })).toBeNull();
  });

  it("passes response headers the browser needs", () => {
    const upstream = new Headers({
      "content-type": "application/json",
      "content-length": "10",
      "content-encoding": "gzip",
      "x-request-id": "r2",
    });
    const headers = pickResponseHeaders(upstream, "fallback");
    expect(headers.get("content-type")).toBe("application/json");
    expect(headers.get("x-request-id")).toBe("r2");
    expect(headers.get("content-length")).toBeNull();
    expect(headers.get("content-encoding")).toBeNull();
    expect(headers.get("cache-control")).toBe("no-store");
  });

  it("passes audio through with its type, length and caching rule", () => {
    const upstream = new Headers({
      "content-type": "audio/mpeg",
      "content-length": "48213",
      "cache-control": "private, no-store",
      "x-content-type-options": "nosniff",
    });
    const headers = pickResponseHeaders(upstream, "r3");
    expect(headers.get("content-type")).toBe("audio/mpeg");
    expect(headers.get("content-length")).toBe("48213");
    expect(headers.get("cache-control")).toBe("private, no-store");
    expect(headers.get("x-content-type-options")).toBe("nosniff");

    const encoded = new Headers({ "content-type": "audio/mpeg", "content-length": "10", "content-encoding": "br" });
    expect(pickResponseHeaders(encoded, "r4").get("content-length")).toBeNull();
    const json = new Headers({ "content-type": "application/json", "content-length": "10" });
    expect(pickResponseHeaders(json, "r5").get("content-length")).toBeNull();
  });

  it("passes byte ranges of a recording both ways", () => {
    const request = buildUpstreamHeaders(new Headers({ range: "bytes=0-1", "if-range": '"v1"' }), { requestId: "r6" });
    expect(request.get("range")).toBe("bytes=0-1");
    expect(request.get("if-range")).toBe('"v1"');

    const partial = pickResponseHeaders(
      new Headers({
        "content-type": "audio/mpeg",
        "content-range": "bytes 0-1/10",
        "accept-ranges": "bytes",
        "content-length": "2",
      }),
      "r7",
    );
    expect(partial.get("content-range")).toBe("bytes 0-1/10");
    expect(partial.get("accept-ranges")).toBe("bytes");
    expect(partial.get("content-length")).toBe("2");
  });

  it("passes idempotency keys and revisions both ways", () => {
    const request = buildUpstreamHeaders(
      new Headers({ "idempotency-key": "key-0000", "if-match": '"7"' }),
      { requestId: "r8" },
    );
    expect(request.get("idempotency-key")).toBe("key-0000");
    expect(request.get("if-match")).toBe('"7"');

    const answer = pickResponseHeaders(new Headers({ etag: '"8"', "idempotent-replayed": "true" }), "r9");
    expect(answer.get("etag")).toBe('"8"');
    expect(answer.get("idempotent-replayed")).toBe("true");
  });

  it("keeps sane request ids and replaces others", () => {
    expect(sanitizeRequestId("abc-123")).toBe("abc-123");
    expect(sanitizeRequestId("bad id\n")).not.toBe("bad id\n");
    expect(sanitizeRequestId("x".repeat(200))).toHaveLength(36);
  });
});

describe("CSRF guard", () => {
  it("lets reads and same-origin writes through", () => {
    expect(isCrossSiteRequest("GET", new Headers({ origin: "https://evil.example" }))).toBe(false);
    expect(isCrossSiteRequest("POST", new Headers({ origin: "https://cabinet.example", host: "cabinet.example" }))).toBe(false);
    expect(isCrossSiteRequest("POST", new Headers({ host: "cabinet.example" }))).toBe(false);
  });

  it("refuses cross-site writes", () => {
    expect(isCrossSiteRequest("POST", new Headers({ origin: "https://evil.example", host: "cabinet.example" }))).toBe(true);
    expect(isCrossSiteRequest("DELETE", new Headers({ "sec-fetch-site": "cross-site" }))).toBe(true);
    expect(
      isCrossSiteRequest(
        "PUT",
        new Headers({ origin: "https://cabinet.example", host: "internal:3000", "x-forwarded-host": "cabinet.example" }),
      ),
    ).toBe(false);
  });
});

describe("configuration", () => {
  it("reads BACKEND_URL without a trailing slash", () => {
    expect(getBackendUrl({})).toBe("http://localhost:8000");
    expect(getBackendUrl({ BACKEND_URL: "https://api.example.com/" })).toBe("https://api.example.com");
  });

  it("makes cookies Secure in production unless switched off", () => {
    expect(isCookieSecure({ NODE_ENV: "production" })).toBe(true);
    expect(isCookieSecure({ NODE_ENV: "development" })).toBe(false);
    expect(isCookieSecure({ NODE_ENV: "production", COOKIE_SECURE: "false" })).toBe(false);
  });

  it("reads API microseconds", () => {
    expect(dateFromMicroseconds(1_793_455_772_935_587).toISOString()).toBe("2026-10-31T14:09:32.935Z");
  });
});

describe("navigation", () => {
  it("only returns to same-site paths after sign-in", () => {
    expect(safeNextPath("/b/business_1/bookings?x=1")).toBe("/b/business_1/bookings?x=1");
    expect(safeNextPath("https://evil.example")).toBe("/businesses");
    expect(safeNextPath("//evil.example")).toBe("/businesses");
    expect(safeNextPath("/\\evil.example")).toBe("/businesses");
    expect(safeNextPath("/login?next=/x")).toBe("/businesses");
    expect(safeNextPath(null)).toBe("/businesses");
    // The URL parser drops tab, LF and CR, so "/\t/evil" would become "//evil".
    expect(safeNextPath("/\t/evil.example")).toBe("/businesses");
    expect(safeNextPath("/\n/evil.example")).toBe("/businesses");
    expect(safeNextPath("/\r/evil.example")).toBe("/businesses");
    expect(safeNextPath("/b/x\u0000")).toBe("/businesses");
    expect(loginPath({ next: "/\t/evil.example", reason: "expired" })).toBe("/login?reason=expired");
  });

  it("builds sign-in links", () => {
    expect(loginPath()).toBe("/login");
    expect(loginPath({ next: "/b/1/leads", reason: "expired" })).toBe("/login?next=%2Fb%2F1%2Fleads&reason=expired");
    expect(loginPath({ next: "/businesses" })).toBe("/login");
  });

  it("knows protected pages and business sections", () => {
    expect(isProtectedPath("/businesses")).toBe(true);
    expect(isProtectedPath("/b/x/dashboard")).toBe(true);
    expect(isProtectedPath("/integrations/google-calendar/callback")).toBe(true);
    expect(isProtectedPath("/admin")).toBe(true);
    expect(isProtectedPath("/create")).toBe(true);
    expect(isProtectedPath("/created")).toBe(false);
    expect(isProtectedPath("/login")).toBe(false);
    expect(isProtectedPath("/businessesX")).toBe(false);
    expect(sectionFromPathname("/b/business_1/bookings/booking_2")).toBe("bookings");
    expect(sectionFromPathname("/businesses")).toBeNull();
  });
});
