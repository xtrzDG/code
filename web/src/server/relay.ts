import "server-only";

import { NextResponse, type NextRequest } from "next/server";

import { LOCALE_COOKIE, matchLocale } from "@/i18n/config";
import { isStepUpChallenge } from "@/lib/stepUpChallenge";

import {
  REQUEST_ID_HEADER,
  buildUpstreamHeaders,
  callBackend,
  isCrossSiteRequest,
  jsonError,
  pickResponseHeaders,
  sanitizeRequestId,
} from "./backend";
import { BodyTooLargeError, bodyLimitFor, isDeclaredTooLarge, limitBodyStream, payloadTooLargeMessage } from "./bodyLimits";
import { clearSessionCookie, readSessionToken } from "./sessionCookie";

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

  const token = options.useSession ? readSessionToken(request.cookies) : undefined;
  const headers = buildUpstreamHeaders(request.headers, {
    token,
    locale: matchLocale(request.cookies.get(LOCALE_COOKIE)?.value),
    requestId,
  });
  return { requestId, headers, token };
}

/**
 * Send the request to `backendPath` (+ the incoming query string) and stream
 * the answer back. A 401 for a request that carried the session ends it,
 * except a step-up challenge (the session stays; the page asks for a code). A
 * body over the path's limit (bodyLimits.ts) is refused with 413 before it
 * reaches the API.
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
  const limit = bodyLimitFor(backendPath);
  if (isDeclaredTooLarge(request.headers, limit)) {
    return jsonError(413, "payload_too_large", payloadTooLargeMessage(limit), requestId);
  }

  let upstream: Response;
  try {
    upstream = await callBackend(`${backendPath}${request.nextUrl.search}`, {
      method: request.method,
      headers,
      body: BODILESS_METHODS.has(request.method) || !request.body ? null : limitBodyStream(request.body, limit),
    });
  } catch (error) {
    if (error instanceof BodyTooLargeError || (error instanceof Error && error.cause instanceof BodyTooLargeError)) {
      return jsonError(413, "payload_too_large", payloadTooLargeMessage(limit), requestId);
    }
    return jsonError(502, "backend_unavailable", "The API is not reachable.", requestId);
  }

  const response = new NextResponse(BODILESS_STATUSES.has(upstream.status) ? null : upstream.body, {
    status: upstream.status,
    headers: pickResponseHeaders(upstream.headers, requestId),
  });
  if (upstream.status === 401 && token && !isStepUpChallenge(upstream.status, upstream.headers)) {
    clearSessionCookie(response);
  }
  return response;
}
