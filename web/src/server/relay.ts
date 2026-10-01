import "server-only";

import { NextResponse, type NextRequest } from "next/server";

import { LOCALE_COOKIE, matchLocale } from "@/i18n/config";

import {
  REQUEST_ID_HEADER,
  SESSION_COOKIE,
  buildUpstreamHeaders,
  callBackend,
  isCrossSiteRequest,
  jsonError,
  pickResponseHeaders,
  sanitizeRequestId,
  sessionCookieOptions,
} from "./backend";

const BODILESS_METHODS: ReadonlySet<string> = new Set(["GET", "HEAD"]);
const BODILESS_STATUSES: ReadonlySet<number> = new Set([101, 204, 205, 304]);

/** Request id, cross-site check and API headers shared by the route handlers. */
export function prepareBackendCall(
  request: NextRequest,
  options: { useSession: boolean },
): { requestId: string; headers: Headers; token: string | undefined } | { refusal: Response } {
  const requestId = sanitizeRequestId(request.headers.get(REQUEST_ID_HEADER));
  if (isCrossSiteRequest(request.method, request.headers)) {
    return { refusal: jsonError(403, "forbidden_origin", "Cross-site request refused.", requestId) };
  }

  const token = options.useSession ? request.cookies.get(SESSION_COOKIE)?.value : undefined;
  const headers = buildUpstreamHeaders(request.headers, {
    token,
    locale: matchLocale(request.cookies.get(LOCALE_COOKIE)?.value),
    requestId,
  });
  return { requestId, headers, token };
}

/**
 * Send the request to `backendPath` (+ the incoming query string) and stream
 * the answer back. A 401 for a request that carried the session ends it.
 */
export async function relayToBackend(
  request: NextRequest,
  backendPath: string,
  options: { useSession: boolean },
): Promise<Response> {
  const prepared = prepareBackendCall(request, options);
  if ("refusal" in prepared) {
    return prepared.refusal;
  }
  const { requestId, headers, token } = prepared;

  let upstream: Response;
  try {
    upstream = await callBackend(`${backendPath}${request.nextUrl.search}`, {
      method: request.method,
      headers,
      body: BODILESS_METHODS.has(request.method) ? null : request.body,
    });
  } catch {
    return jsonError(502, "backend_unavailable", "The API is not reachable.", requestId);
  }

  const response = new NextResponse(BODILESS_STATUSES.has(upstream.status) ? null : upstream.body, {
    status: upstream.status,
    headers: pickResponseHeaders(upstream.headers, requestId),
  });
  if (upstream.status === 401 && token) {
    clearSessionCookie(response);
  }
  return response;
}

export function clearSessionCookie(response: NextResponse): void {
  response.cookies.set(SESSION_COOKIE, "", { ...sessionCookieOptions(), maxAge: 0 });
}
