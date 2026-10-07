import { NextRequest, NextResponse } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  LEGACY_SESSION_COOKIE,
  SECURE_SESSION_COOKIE,
  clearSessionCookie,
  migrateLegacySessionCookie,
  readSessionToken,
  sessionCookieName,
  setSessionCookie,
} from "./sessionCookie";

function requestWith(cookie: string): NextRequest {
  return new NextRequest("https://cabinet.example/b/biz_1", { headers: { cookie } });
}

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("session cookie", () => {
  it("is __Host- over HTTPS and keeps its old name on plain HTTP", () => {
    expect(sessionCookieName({ NODE_ENV: "production" })).toBe(SECURE_SESSION_COOKIE);
    expect(sessionCookieName({ NODE_ENV: "production", COOKIE_SECURE: "false" })).toBe(LEGACY_SESSION_COOKIE);
    expect(sessionCookieName({ NODE_ENV: "development" })).toBe(LEGACY_SESSION_COOKIE);
  });

  it("reads the new cookie first and falls back to the old name", () => {
    const env = { NODE_ENV: "production" };
    expect(readSessionToken(requestWith("__Host-aw_session=new; aw_session=old").cookies, env)).toBe("new");
    expect(readSessionToken(requestWith("aw_session=old").cookies, env)).toBe("old");
    expect(readSessionToken(requestWith("aw_locale=en").cookies, env)).toBeUndefined();
  });

  it("is set as a Secure, host-only, httpOnly cookie over HTTPS", () => {
    vi.stubEnv("COOKIE_SECURE", "true");
    const response = NextResponse.next();

    setSessionCookie(response, "tok", new Date("2026-11-01T00:00:00Z"));

    const header = response.headers.get("set-cookie") ?? "";
    expect(header).toMatch(/^__Host-aw_session=tok; Path=\/; Expires=Sun, 01 Nov 2026 00:00:00 GMT; Secure; HttpOnly; SameSite=lax$/i);
    expect(header).not.toMatch(/Domain=/i);
  });

  it("moves an old session to the __Host- cookie and drops the old one", () => {
    vi.stubEnv("COOKIE_SECURE", "true");
    const response = NextResponse.next();

    migrateLegacySessionCookie(requestWith("aw_session=old"), response);

    expect(response.cookies.get(SECURE_SESSION_COOKIE)?.value).toBe("old");
    expect(response.cookies.get(LEGACY_SESSION_COOKIE)?.value).toBe("");
    const untouched = NextResponse.next();
    migrateLegacySessionCookie(requestWith("__Host-aw_session=new"), untouched);
    expect(untouched.headers.get("set-cookie")).toBeNull();
  });

  it("migrates nothing on plain HTTP, where both names are the same", () => {
    vi.stubEnv("COOKIE_SECURE", "false");
    const response = NextResponse.next();

    migrateLegacySessionCookie(requestWith("aw_session=old"), response);

    expect(response.headers.get("set-cookie")).toBeNull();
  });

  it("is cleared under both names", () => {
    vi.stubEnv("COOKIE_SECURE", "true");
    const response = NextResponse.next();

    clearSessionCookie(response);

    expect(response.cookies.get(SECURE_SESSION_COOKIE)?.value).toBe("");
    expect(response.cookies.get(LEGACY_SESSION_COOKIE)?.value).toBe("");
  });
});
