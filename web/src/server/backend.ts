/**
 * Talking to the Python API from the Next.js server (route handlers, the
 * proxy and Server Components). Browser code never imports this module: it
 * calls /api/backend/* instead, and the bearer token stays in an httpOnly
 * cookie here on the server.
 */

import { LOCALE_COOKIE_MAX_AGE_SECONDS, type Locale } from "@/i18n/config";
import type { ApiErrorCode } from "@/api/errors";

/** Request header the proxy sets so Server Components know the current path. */
export const PATHNAME_HEADER = "x-aw-pathname";

export const REQUEST_ID_HEADER = "x-request-id";

const DEFAULT_BACKEND_URL = "http://localhost:8000";

/** Long LLM-backed calls (assembly, autotests, test chat, menu import) need time. */
const UPSTREAM_TIMEOUT_MS = 180_000;

const MAX_REQUEST_ID_LENGTH = 128;

/** Base URL of the API from BACKEND_URL, without a trailing slash. */
export function getBackendUrl(env: Record<string, string | undefined> = process.env): string {
  const configured = env.BACKEND_URL?.trim();
  return (configured ? configured : DEFAULT_BACKEND_URL).replace(/\/+$/, "");
}

/** Secure cookies in production unless COOKIE_SECURE=false (plain-HTTP staging). */
export function isCookieSecure(env: Record<string, string | undefined> = process.env): boolean {
  if (env.COOKIE_SECURE === "false") {
    return false;
  }
  if (env.COOKIE_SECURE === "true") {
    return true;
  }
  return env.NODE_ENV === "production";
}

export interface CookieOptions {
  httpOnly: boolean;
  secure: boolean;
  sameSite: "lax";
  path: string;
  expires?: Date;
  maxAge?: number;
}

export function sessionCookieOptions(expires?: Date): CookieOptions {
  return {
    httpOnly: true,
    secure: isCookieSecure(),
    sameSite: "lax",
    path: "/",
    ...(expires ? { expires } : {}),
  };
}

export function localeCookieOptions(): CookieOptions {
  return {
    httpOnly: false,
    secure: isCookieSecure(),
    sameSite: "lax",
    path: "/",
    maxAge: LOCALE_COOKIE_MAX_AGE_SECONDS,
  };
}

/** The API sends times as UNIX microseconds. */
export function dateFromMicroseconds(microseconds: number): Date {
  return new Date(Math.floor(microseconds / 1000));
}

/**
 * The API path for the segments after /api/backend, or null when the path is
 * not an API route ("/v1/...") or tries to escape it ("..", empty segments).
 */
export function buildBackendPath(segments: readonly string[]): string | null {
  if (segments.length < 2 || segments[0] !== "v1") {
    return null;
  }
  if (segments.some((segment) => segment === "" || segment === "." || segment === "..")) {
    return null;
  }
  return `/${segments.map((segment) => encodeURIComponent(segment)).join("/")}`;
}

/** A caller's request id if it is short printable ASCII, else a new one. */
export function sanitizeRequestId(value: string | null | undefined): string {
  if (value && value.length <= MAX_REQUEST_ID_LENGTH && /^[\x21-\x7e]+$/.test(value)) {
    return value;
  }
  return crypto.randomUUID();
}

/** `range` and `if-range`: media players ask for parts of a recording. */
const FORWARDED_REQUEST_HEADERS = [
  "accept",
  "content-type",
  "user-agent",
  "range",
  "if-range",
  // One key per user action, so a retry is answered, not repeated.
  "idempotency-key",
  "if-match",
] as const;

/**
 * The X-Forwarded-For hops the cabinet's own proxies added: the right-most
 * TRUSTED_PROXY_HOPS entries (default 0, header dropped). The rest of the
 * header comes from the browser and could be forged, and Next.js keeps a
 * header the browser sent instead of appending the peer address.
 */
export function trustedForwardedFor(
  incoming: Headers | null,
  env: Record<string, string | undefined> = process.env,
): string | null {
  const hops = Number.parseInt(env.TRUSTED_PROXY_HOPS ?? "0", 10);
  const raw = incoming?.get("x-forwarded-for");
  if (!raw || !Number.isInteger(hops) || hops <= 0) {
    return null;
  }
  const entries = raw
    .split(",")
    .map((entry) => entry.trim())
    .filter(Boolean);
  const kept = entries.slice(-hops);
  return kept.length > 0 ? kept.join(", ") : null;
}

/**
 * Headers for an API call: a small allow-list of the incoming ones (never
 * the cookies), the client address the cabinet's proxies vouch for, the
 * bearer token, the interface language and the request id.
 */
export function buildUpstreamHeaders(
  incoming: Headers | null,
  options: { token?: string | null; locale?: Locale | null; requestId: string },
): Headers {
  const headers = new Headers();
  for (const name of FORWARDED_REQUEST_HEADERS) {
    const value = incoming?.get(name);
    if (value) {
      headers.set(name, value);
    }
  }
  const forwardedFor = trustedForwardedFor(incoming);
  if (forwardedFor) {
    headers.set("x-forwarded-for", forwardedFor);
  }

  const acceptLanguage = incoming?.get("accept-language");
  if (options.locale) {
    headers.set("accept-language", `${options.locale}, en;q=0.5`);
  } else if (acceptLanguage) {
    headers.set("accept-language", acceptLanguage);
  }

  if (options.token) {
    headers.set("authorization", `Bearer ${options.token}`);
  }
  headers.set(REQUEST_ID_HEADER, options.requestId);
  return headers;
}

const FORWARDED_RESPONSE_HEADERS = [
  "content-type",
  "content-disposition",
  "cache-control",
  "retry-after",
  // A 401 asking to confirm a sensitive action says so here (step-up).
  "www-authenticate",
  "x-content-type-options",
  // A media player seeks and (Safari, iOS) plays only with byte ranges.
  "accept-ranges",
  "content-range",
  // The settings revision, and whether an answer is a replay of a retry.
  "etag",
  "idempotent-replayed",
  REQUEST_ID_HEADER,
] as const;

/** Binary media the API streams (call recordings), passed on byte for byte. */
const MEDIA_CONTENT_TYPE = /^(audio|video)\//i;

/**
 * Headers of the API response passed to the browser. Encoding is dropped:
 * fetch has already decoded the body. So is the length, except for audio
 * and video the API sent unencoded (the body is then the same bytes), which
 * lets the browser's player show the duration and progress.
 */
export function pickResponseHeaders(upstream: Headers, requestId: string): Headers {
  const headers = new Headers();
  for (const name of FORWARDED_RESPONSE_HEADERS) {
    const value = upstream.get(name);
    if (value) {
      headers.set(name, value);
    }
  }
  const length = upstream.get("content-length");
  if (length && /^\d+$/.test(length) && !upstream.has("content-encoding") && MEDIA_CONTENT_TYPE.test(upstream.get("content-type") ?? "")) {
    headers.set("content-length", length);
  }
  if (!headers.has(REQUEST_ID_HEADER)) {
    headers.set(REQUEST_ID_HEADER, requestId);
  }
  if (!headers.has("cache-control")) {
    headers.set("cache-control", "no-store");
  }
  return headers;
}

const SAFE_METHODS: ReadonlySet<string> = new Set(["GET", "HEAD", "OPTIONS"]);

/**
 * True for a state-changing request sent by another site. The session cookie
 * is SameSite=Lax already; this also refuses cross-site requests that
 * carry it by other means (defence in depth against CSRF).
 */
export function isCrossSiteRequest(method: string, headers: Headers): boolean {
  if (SAFE_METHODS.has(method.toUpperCase())) {
    return false;
  }
  const fetchSite = headers.get("sec-fetch-site");
  if (fetchSite === "cross-site") {
    return true;
  }
  const origin = headers.get("origin");
  if (!origin) {
    return false;
  }
  const host = headers.get("x-forwarded-host") ?? headers.get("host");
  try {
    return host !== null && new URL(origin).host !== host.split(",")[0]?.trim();
  } catch {
    return true;
  }
}

/** An error answer in the backend's own format. */
export function jsonError(
  status: number,
  code: ApiErrorCode,
  message: string,
  requestId: string,
): Response {
  return Response.json(
    { error: code, message },
    { status, headers: { [REQUEST_ID_HEADER]: requestId, "cache-control": "no-store" } },
  );
}

/**
 * Call the API from the server. Network failures and timeouts throw
 * (callers answer 502 `backend_unavailable`).
 */
export async function callBackend(
  path: string,
  init: {
    method?: string;
    body?: BodyInit | null;
    headers: Headers;
    timeoutMs?: number;
  },
): Promise<Response> {
  const requestInit: RequestInit & { duplex?: "half" } = {
    method: init.method ?? "GET",
    headers: init.headers,
    body: init.body ?? null,
    redirect: "manual",
    cache: "no-store",
    signal: AbortSignal.timeout(init.timeoutMs ?? UPSTREAM_TIMEOUT_MS),
  };
  if (init.body instanceof ReadableStream) {
    // Streaming request bodies need half-duplex in Node's fetch.
    requestInit.duplex = "half";
  }
  return fetch(`${getBackendUrl()}${path}`, requestInit);
}
