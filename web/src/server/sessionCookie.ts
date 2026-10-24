/**
 * The httpOnly cookie with the API bearer token.
 *
 * Over HTTPS it is `__Host-aw_session`: the browser takes it only with
 * Secure, Path=/ and no Domain, so no subdomain and no plain-HTTP page can
 * set or shadow it. A plain-HTTP deployment (COOKIE_SECURE=false: local
 * runs, staging without TLS) keeps `aw_session`, because a `__Host-` cookie
 * needs Secure. A browser that still has the old `aw_session` from before
 * the rename keeps its session: it is read as a fallback and moved to the
 * new name on the next page view (`migrateLegacySessionCookie`).
 */

import type { NextRequest, NextResponse } from "next/server";

import { isCookieSecure, sessionCookieOptions } from "./backend";

/** The cookie name before the `__Host-` prefix, and on plain HTTP. */
export const LEGACY_SESSION_COOKIE = "aw_session";
export const SECURE_SESSION_COOKIE = "__Host-aw_session";

/** Cookies migrated from the old name live as long as a new session (30 days). */
const MIGRATED_SESSION_MAX_AGE_SECONDS = 30 * 24 * 60 * 60;

type Env = Record<string, string | undefined>;

interface CookieReader {
  get(name: string): { value: string } | undefined;
}

export function sessionCookieName(env: Env = process.env): string {
  return isCookieSecure(env) ? SECURE_SESSION_COOKIE : LEGACY_SESSION_COOKIE;
}

/** The session token: the current cookie, else one under the old name. */
export function readSessionToken(cookies: CookieReader, env: Env = process.env): string | undefined {
  return cookies.get(sessionCookieName(env))?.value || cookies.get(LEGACY_SESSION_COOKIE)?.value || undefined;
}

export function setSessionCookie(response: NextResponse, token: string, expires: Date): void {
  response.cookies.set(sessionCookieName(), token, sessionCookieOptions(expires));
}

/** Drop the session under both names (sign-out, a rejected token). */
export function clearSessionCookie(response: NextResponse): void {
  const name = sessionCookieName();
  response.cookies.set(name, "", { ...sessionCookieOptions(), maxAge: 0 });
  if (name !== LEGACY_SESSION_COOKIE) {
    response.cookies.set(LEGACY_SESSION_COOKIE, "", { ...sessionCookieOptions(), secure: false, maxAge: 0 });
  }
}

/** Move a session under the old name to the `__Host-` cookie (HTTPS only). */
export function migrateLegacySessionCookie(request: NextRequest, response: NextResponse): void {
  const name = sessionCookieName();
  const legacy = request.cookies.get(LEGACY_SESSION_COOKIE)?.value;
  if (name === LEGACY_SESSION_COOKIE || !legacy) {
    return;
  }
  if (!request.cookies.get(name)?.value) {
    response.cookies.set(name, legacy, { ...sessionCookieOptions(), maxAge: MIGRATED_SESSION_MAX_AGE_SECONDS });
  }
  response.cookies.set(LEGACY_SESSION_COOKIE, "", { ...sessionCookieOptions(), secure: false, maxAge: 0 });
}
