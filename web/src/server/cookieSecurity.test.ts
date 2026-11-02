import { describe, expect, it } from "vitest";

import { isCookieSecure, isLocalPlainHttpRequest, localeCookieOptions, sessionCookieOptions } from "./cookieSecurity";

const PRODUCTION = { NODE_ENV: "production" };
const PLAIN_HTTP_RUN = { NODE_ENV: "production", COOKIE_SECURE: "false" };

/** A request as `next start` sees it: Next adds X-Forwarded-Host and -Proto when no proxy did. */
function from(host: string, extra: Record<string, string> = {}): Headers {
  return new Headers({ host, "x-forwarded-host": host, "x-forwarded-proto": "http", ...extra });
}

describe("Secure cookies", () => {
  it("are on in production and off in development unless COOKIE_SECURE says otherwise", () => {
    expect(isCookieSecure(from("app.example.com"), PRODUCTION)).toBe(true);
    expect(isCookieSecure(null, PRODUCTION)).toBe(true);
    expect(isCookieSecure(from("localhost:3000"), { NODE_ENV: "development" })).toBe(false);
    expect(isCookieSecure(from("localhost:3000"), { NODE_ENV: "development", COOKIE_SECURE: "true" })).toBe(true);
    expect(isCookieSecure(from("localhost:3000"), { NODE_ENV: "test" })).toBe(false);
  });

  it("honour COOKIE_SECURE=false for a run on this machine over plain HTTP (the e2e suite, docker compose)", () => {
    // e2e/playwright.config.ts: next start on http://localhost:3010 with COOKIE_SECURE=false.
    expect(isCookieSecure(from("localhost:3010"), PLAIN_HTTP_RUN)).toBe(false);
    expect(isCookieSecure(from("127.0.0.1:3000"), PLAIN_HTTP_RUN)).toBe(false);
    expect(isCookieSecure(from("[::1]:3000"), PLAIN_HTTP_RUN)).toBe(false);
    expect(isCookieSecure(new Headers({ host: "localhost" }), PLAIN_HTTP_RUN)).toBe(false);
    // The Lighthouse job names its local address as SITE_URL.
    expect(isCookieSecure(from("localhost:3020"), { ...PLAIN_HTTP_RUN, SITE_URL: "http://localhost:3020" })).toBe(false);
  });

  it("stay on in a real deployment that kept COOKIE_SECURE=false", () => {
    expect(isCookieSecure(from("app.example.com"), PLAIN_HTTP_RUN)).toBe(true);
    // Behind a TLS proxy, or a proxy that names another host.
    expect(isCookieSecure(from("localhost:3000", { "x-forwarded-proto": "https" }), PLAIN_HTTP_RUN)).toBe(true);
    expect(isCookieSecure(from("localhost:3000", { "x-forwarded-host": "app.example.com" }), PLAIN_HTTP_RUN)).toBe(true);
    // SITE_URL names the real site.
    expect(isCookieSecure(from("localhost:3000"), { ...PLAIN_HTTP_RUN, SITE_URL: "https://app.example.com" })).toBe(true);
    expect(isCookieSecure(from("localhost:3000"), { ...PLAIN_HTTP_RUN, SITE_URL: "https://localhost" })).toBe(true);
    // Hosts that only look local.
    expect(isCookieSecure(from("localhost.example.com"), PLAIN_HTTP_RUN)).toBe(true);
    expect(isCookieSecure(from("localhost:3000@evil.example"), PLAIN_HTTP_RUN)).toBe(true);
    expect(isCookieSecure(from("10.0.0.5:3000"), PLAIN_HTTP_RUN)).toBe(true);
    expect(isCookieSecure(new Headers(), PLAIN_HTTP_RUN)).toBe(true);
    expect(isCookieSecure(null, PLAIN_HTTP_RUN)).toBe(true);
  });

  it("reads only the first entry of a forwarded list", () => {
    expect(isLocalPlainHttpRequest(from("localhost:3000", { "x-forwarded-host": "localhost:3000, app.example.com" }), PLAIN_HTTP_RUN)).toBe(true);
    expect(isLocalPlainHttpRequest(from("localhost:3000", { "x-forwarded-proto": "https, http" }), PLAIN_HTTP_RUN)).toBe(false);
  });
});

describe("cookie options", () => {
  it("give the session and the language cookie the request's Secure flag", () => {
    const expires = new Date("2026-12-01T00:00:00Z");
    expect(sessionCookieOptions(from("app.example.com"), expires)).toEqual({ httpOnly: true, secure: false, sameSite: "lax", path: "/", expires });
    expect(localeCookieOptions(from("app.example.com"))).toMatchObject({ httpOnly: false, sameSite: "lax", path: "/", maxAge: 365 * 24 * 60 * 60 });
  });
});
