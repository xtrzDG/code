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
      "x-forwarded-for": "203.0.113.5",
      host: "cabinet.example",
    });
    const headers = buildUpstreamHeaders(incoming, { token: "tok", locale: "ka", requestId: "r1" });
    expect(headers.get("authorization")).toBe("Bearer tok");
    expect(headers.get("accept-language")).toBe("ka, en;q=0.5");
    expect(headers.get("content-type")).toBe("application/json");
    expect(headers.get("x-forwarded-for")).toBe("203.0.113.5");
    expect(headers.get("x-request-id")).toBe("r1");
    expect(headers.get("cookie")).toBeNull();
    expect(headers.get("host")).toBeNull();
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
  });

  it("builds sign-in links", () => {
    expect(loginPath()).toBe("/login");
    expect(loginPath({ next: "/b/1/leads", reason: "expired" })).toBe("/login?next=%2Fb%2F1%2Fleads&reason=expired");
    expect(loginPath({ next: "/businesses" })).toBe("/login");
  });

  it("knows protected pages and business sections", () => {
    expect(isProtectedPath("/businesses")).toBe(true);
    expect(isProtectedPath("/b/x/dashboard")).toBe(true);
    expect(isProtectedPath("/admin")).toBe(true);
    expect(isProtectedPath("/login")).toBe(false);
    expect(isProtectedPath("/businessesX")).toBe(false);
    expect(sectionFromPathname("/b/business_1/bookings/booking_2")).toBe("bookings");
    expect(sectionFromPathname("/businesses")).toBeNull();
  });
});
