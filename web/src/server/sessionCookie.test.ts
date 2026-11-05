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

const PRODUCTION = { NODE_ENV: "production" };
const COOKIE_SECURE_TRUE_IN_DEVELOPMENT = { NODE_ENV: "development", COOKIE_SECURE: "true" };

function requestWith(cookie: string, url = "https://cabinet.example/b/biz_1"): NextRequest {
  return new NextRequest(url, { headers: { cookie, host: new URL(url).host } });
}

const site = new Headers({ host: "cabinet.example", "x-forwarded-proto": "https" });
const localRun = new Headers({ host: "localhost:3010", "x-forwarded-host": "localhost:3010", "x-forwarded-proto": "http" });

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("session cookie", () => {
  it("is __Host- in production and keeps its old name on plain HTTP", () => {
    expect(sessionCookieName(site, PRODUCTION)).toBe(SECURE_SESSION_COOKIE);
    expect(sessionCookieName(localRun, { NODE_ENV: "production", COOKIE_SECURE: "false" })).toBe(LEGACY_SESSION_COOKIE);
    expect(sessionCookieName(localRun, { NODE_ENV: "development" })).toBe(LEGACY_SESSION_COOKIE);
  });

  it("stays __Host- in a real deployment that kept COOKIE_SECURE=false", () => {
    expect(sessionCookieName(site, { NODE_ENV: "production", COOKIE_SECURE: "false" })).toBe(SECURE_SESSION_COOKIE);
  });

  it("never reads the old name in production", () => {
    expect(readSessionToken(requestWith("__Host-aw_session=new; aw_session=old").cookies, site, PRODUCTION)).toBe("new");
    // A cookie a subdomain or a plain-HTTP page could have planted.
    expect(readSessionToken(requestWith("aw_session=planted").cookies, site, PRODUCTION)).toBeUndefined();
    expect(readSessionToken(requestWith("aw_locale=en").cookies, site, PRODUCTION)).toBeUndefined();
  });

  it("falls back to the old name outside production", () => {
    expect(readSessionToken(requestWith("aw_session=old").cookies, site, COOKIE_SECURE_TRUE_IN_DEVELOPMENT)).toBe("old");
    expect(readSessionToken(requestWith("__Host-aw_session=new; aw_session=old").cookies, site, COOKIE_SECURE_TRUE_IN_DEVELOPMENT)).toBe("new");
  });

  it("is read under its plain-HTTP name on a local run", () => {
    const env = { NODE_ENV: "production", COOKIE_SECURE: "false" };
    expect(readSessionToken(requestWith("aw_session=tok", "http://localhost:3010/b/x").cookies, localRun, env)).toBe("tok");
    expect(readSessionToken(requestWith("__Host-aw_session=tok", "http://localhost:3010/b/x").cookies, localRun, env)).toBeUndefined();
  });

  it("is set as a Secure, host-only, httpOnly cookie over HTTPS", () => {
    vi.stubEnv("COOKIE_SECURE", "true");
    const response = NextResponse.next();

    setSessionCookie(response, "tok", new Date("2026-11-01T00:00:00Z"), site);

    expect(response.cookies.get(SECURE_SESSION_COOKIE)).toMatchObject({
      value: "tok",
      httpOnly: true,
      secure: true,
      sameSite: "lax",
      path: "/",
    });
    expect(response.cookies.get(SECURE_SESSION_COOKIE)?.domain).toBeUndefined();
  });

  it("moves a session under the old name to the new one outside production", () => {
    vi.stubEnv("COOKIE_SECURE", "true");
    const response = NextResponse.next();

    migrateLegacySessionCookie(requestWith("aw_session=old"), response, COOKIE_SECURE_TRUE_IN_DEVELOPMENT);

    expect(response.cookies.get(SECURE_SESSION_COOKIE)?.value).toBe("old");
    expect(response.cookies.get(LEGACY_SESSION_COOKIE)?.value).toBe("");
    const untouched = NextResponse.next();
    migrateLegacySessionCookie(requestWith("__Host-aw_session=new"), untouched, COOKIE_SECURE_TRUE_IN_DEVELOPMENT);
    expect(untouched.cookies.getAll()).toEqual([]);
  });

  it("only drops a cookie under the old name in production", () => {
    const response = NextResponse.next();

    migrateLegacySessionCookie(requestWith("aw_session=planted"), response, PRODUCTION);

    expect(response.cookies.get(SECURE_SESSION_COOKIE)).toBeUndefined();
    expect(response.cookies.get(LEGACY_SESSION_COOKIE)).toMatchObject({ value: "", maxAge: 0, secure: false });
  });

  it("leaves the plain-HTTP session alone", () => {
    const response = NextResponse.next();

    migrateLegacySessionCookie(requestWith("aw_session=tok", "http://localhost:3010/b/x"), response, {
      NODE_ENV: "production",
      COOKIE_SECURE: "false",
    });

    expect(response.cookies.getAll()).toEqual([]);
  });

  it("is dropped under both names", () => {
    const response = NextResponse.next();

    clearSessionCookie(response);

    expect(response.cookies.get(SECURE_SESSION_COOKIE)).toMatchObject({ value: "", maxAge: 0, secure: true, path: "/" });
    expect(response.cookies.get(LEGACY_SESSION_COOKIE)).toMatchObject({ value: "", maxAge: 0, secure: false, path: "/" });
  });
});
