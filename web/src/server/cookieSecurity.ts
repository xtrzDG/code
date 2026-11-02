/**
 * Whether the cabinet's cookies carry `Secure` (and the session cookie the
 * `__Host-` name), decided per request:
 *  - always in a production build; COOKIE_SECURE=false lifts it only for a
 *    run on this machine over plain HTTP, the way the end-to-end tests and
 *    docker compose start `next start` (http://localhost, 127.0.0.1 or
 *    [::1]): the request must come in on such an address, no proxy in front
 *    may report HTTPS or another host, and SITE_URL, when set, must be such
 *    an address too. A real deployment that still has COOKIE_SECURE=false in
 *    its settings keeps Secure cookies;
 *  - never in development (`next dev`), unless COOKIE_SECURE=true.
 */

import { LOCALE_COOKIE_MAX_AGE_SECONDS } from "@/i18n/config";

type Env = Record<string, string | undefined>;
export type HeaderReader = Pick<Headers, "get">;

const LOCAL_HOSTNAMES: ReadonlySet<string> = new Set(["localhost", "127.0.0.1", "[::1]"]);

/** "localhost:3010", "127.0.0.1" or "[::1]:3000" (the first entry of a list), nothing else. */
function isLocalHost(value: string | null): boolean {
  const host = value?.split(",")[0]?.trim().toLowerCase() ?? "";
  if (host === "") {
    return false;
  }
  try {
    const url = new URL(`http://${host}`);
    return url.host === host && LOCAL_HOSTNAMES.has(url.hostname);
  } catch {
    return false;
  }
}

function isLocalPlainHttpAddress(value: string): boolean {
  try {
    const url = new URL(value);
    return url.protocol === "http:" && LOCAL_HOSTNAMES.has(url.hostname);
  } catch {
    return false;
  }
}

/** A request to a cabinet on this machine over plain HTTP (see the module comment). */
export function isLocalPlainHttpRequest(headers: HeaderReader | null, env: Env = process.env): boolean {
  if (headers === null) {
    return false;
  }
  const site = env.SITE_URL?.trim();
  if (site && !isLocalPlainHttpAddress(site)) {
    return false;
  }
  const forwardedProto = headers.get("x-forwarded-proto")?.split(",")[0]?.trim().toLowerCase();
  if (forwardedProto !== undefined && forwardedProto !== "" && forwardedProto !== "http") {
    return false;
  }
  const forwardedHost = headers.get("x-forwarded-host");
  if (forwardedHost !== null && !isLocalHost(forwardedHost)) {
    return false;
  }
  return isLocalHost(headers.get("host"));
}

/** Secure cookies for this request (`headers`: the browser's request; null outside one). */
export function isCookieSecure(headers: HeaderReader | null, env: Env = process.env): boolean {
  if (env.COOKIE_SECURE === "true") {
    return true;
  }
  if (env.NODE_ENV !== "production") {
    return false;
  }
  return !(env.COOKIE_SECURE === "false" && isLocalPlainHttpRequest(headers, env));
}

export interface CookieOptions {
  httpOnly: boolean;
  secure: boolean;
  sameSite: "lax";
  path: string;
  expires?: Date;
  maxAge?: number;
}

export function sessionCookieOptions(headers: HeaderReader | null, expires?: Date): CookieOptions {
  return {
    httpOnly: true,
    secure: isCookieSecure(headers),
    sameSite: "lax",
    path: "/",
    ...(expires ? { expires } : {}),
  };
}

export function localeCookieOptions(headers: HeaderReader | null): CookieOptions {
  return {
    httpOnly: false,
    secure: isCookieSecure(headers),
    sameSite: "lax",
    path: "/",
    maxAge: LOCALE_COOKIE_MAX_AGE_SECONDS,
  };
}
