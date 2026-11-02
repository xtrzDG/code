/**
 * The httpOnly cookie with the API bearer token.
 *
 * With Secure cookies (cookieSecurity.ts: every production deployment) it
 * is `__Host-aw_session`: the browser takes it only with Secure, Path=/
 * and no Domain, so no subdomain and no plain-HTTP page can set or shadow
 * it. Without them (development, a production build run over plain HTTP
 * on this machine) it is `aw_session`, because a `__Host-` cookie needs
 * Secure.
 *
 * `aw_session` is also the cookie's name from before the `__Host-` rename.
 * In production it is never read where the session is `__Host-aw_session`:
 * a subdomain or a plain-HTTP page could have planted it (a session of
 * the attacker's choosing), so the proxy only drops it. Outside production
 * a session under the old name is still read and moved to the new one.
 */

import type { NextRequest, NextResponse } from "next/server";

import { isCookieSecure, sessionCookieOptions, type HeaderReader } from "./cookieSecurity";

/** The cookie name before the `__Host-` prefix, and on plain HTTP. */
export const LEGACY_SESSION_COOKIE = "aw_session";
export const SECURE_SESSION_COOKIE = "__Host-aw_session";

/** Cookies migrated from the old name live as long as a new session (30 days). */
const MIGRATED_SESSION_MAX_AGE_SECONDS = 30 * 24 * 60 * 60;

type Env = Record<string, string | undefined>;

interface CookieReader {
  get(name: string): { value: string } | undefined;
}

export function sessionCookieName(headers: HeaderReader | null, env: Env = process.env): string {
  return isCookieSecure(headers, env) ? SECURE_SESSION_COOKIE : LEGACY_SESSION_COOKIE;
}

/** The old name is read (and moved) only outside production. */
function readsLegacyName(env: Env): boolean {
  return env.NODE_ENV !== "production";
}

/** The session token of a request: its cookie, else (outside production) one under the old name. */
export function readSessionToken(cookies: CookieReader, headers: HeaderReader | null, env: Env = process.env): string | undefined {
  const name = sessionCookieName(headers, env);
  const current = cookies.get(name)?.value;
  if (current) {
    return current;
  }
  if (name !== LEGACY_SESSION_COOKIE && readsLegacyName(env)) {
    return cookies.get(LEGACY_SESSION_COOKIE)?.value || undefined;
  }
  return undefined;
}

export function setSessionCookie(response: NextResponse, token: string, expires: Date, headers: HeaderReader | null): void {
  response.cookies.set(sessionCookieName(headers), token, sessionCookieOptions(headers, expires));
}

/** Drop the session under both names (sign-out, a rejected token). */
export function clearSessionCookie(response: NextResponse): void {
  response.cookies.set(SECURE_SESSION_COOKIE, "", { ...sessionCookieOptions(null), secure: true, maxAge: 0 });
  response.cookies.set(LEGACY_SESSION_COOKIE, "", { ...sessionCookieOptions(null), secure: false, maxAge: 0 });
}

/**
 * A request with a cookie under the old name where the session is
 * `__Host-aw_session`: outside production the session moves to the new
 * name; in production the old cookie is only dropped, never read.
 */
export function migrateLegacySessionCookie(request: NextRequest, response: NextResponse, env: Env = process.env): void {
  const name = sessionCookieName(request.headers, env);
  const legacy = request.cookies.get(LEGACY_SESSION_COOKIE)?.value;
  if (name === LEGACY_SESSION_COOKIE || !legacy) {
    return;
  }
  if (readsLegacyName(env) && !request.cookies.get(name)?.value) {
    response.cookies.set(name, legacy, { ...sessionCookieOptions(request.headers), maxAge: MIGRATED_SESSION_MAX_AGE_SECONDS });
  }
  response.cookies.set(LEGACY_SESSION_COOKIE, "", { ...sessionCookieOptions(null), secure: false, maxAge: 0 });
}
