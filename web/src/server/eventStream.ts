import "server-only";

/**
 * The live event stream of a business (GET …/events, Server-Sent Events)
 * through the BFF. Unlike other API calls it has no overall time limit:
 * it lives until the browser closes it (the request's signal) or the API
 * ends it; only the wait for the API's first answer is bounded. Every
 * chunk is passed on as it arrives: nothing buffers or compresses it
 * (`no-transform`), and proxies are told not to buffer it either.
 */

import { NextResponse, type NextRequest } from "next/server";

import { getBackendUrl, jsonError, pickResponseHeaders } from "./backend";
import { prepareBackendCall } from "./relay";
import { clearSessionCookie } from "./sessionCookie";

/** Answers the API must start within (the stream itself may run for long). */
export const EVENT_STREAM_CONNECT_TIMEOUT_MS = 15_000;

const EVENT_STREAM_PATH = /^\/v1\/businesses\/[^/]+\/events$/;
const EVENT_STREAM_TYPE = /^text\/event-stream/i;

/** Whether a GET to this API path is a live event stream. */
export function isEventStreamPath(method: string, backendPath: string): boolean {
  return method === "GET" && EVENT_STREAM_PATH.test(backendPath);
}

/** Headers of a streamed answer: never cached, transformed or buffered on the way. */
export function eventStreamHeaders(upstream: Headers, requestId: string): Headers {
  const headers = pickResponseHeaders(upstream, requestId);
  if (EVENT_STREAM_TYPE.test(upstream.get("content-type") ?? "")) {
    headers.set("cache-control", "no-cache, no-transform");
    headers.set("x-accel-buffering", "no");
  }
  return headers;
}

/**
 * Relays the stream. The upstream request ends with the browser's (a closed
 * tab ends it at the API too); a stream the API never starts answering
 * within EVENT_STREAM_CONNECT_TIMEOUT_MS is answered with 504. The last
 * event id the browser saw goes along, so the API replays what it missed.
 */
export async function relayEventStream(
  request: NextRequest,
  backendPath: string,
  connectTimeoutMs: number = EVENT_STREAM_CONNECT_TIMEOUT_MS,
): Promise<Response> {
  const prepared = prepareBackendCall(request, { useSession: true });
  if ("refusal" in prepared) {
    return prepared.refusal;
  }
  const { requestId, headers, token } = prepared;
  const lastEventId = request.headers.get("last-event-id");
  if (lastEventId) {
    headers.set("last-event-id", lastEventId);
  }
  headers.set("accept", "text/event-stream");

  const upstreamAbort = new AbortController();
  const stopWithBrowser = () => upstreamAbort.abort(request.signal.reason);
  request.signal.addEventListener("abort", stopWithBrowser, { once: true });
  let didTimeOut = false;
  const connectTimer = setTimeout(() => {
    didTimeOut = true;
    upstreamAbort.abort(new Error("connect timeout"));
  }, connectTimeoutMs);

  let upstream: Response;
  try {
    upstream = await fetch(`${getBackendUrl()}${backendPath}${request.nextUrl.search}`, {
      method: "GET",
      headers,
      redirect: "manual",
      cache: "no-store",
      signal: upstreamAbort.signal,
    });
  } catch {
    request.signal.removeEventListener("abort", stopWithBrowser);
    return didTimeOut
      ? jsonError(504, "backend_unavailable", "The API did not answer in time.", requestId)
      : jsonError(502, "backend_unavailable", "The API is not reachable.", requestId);
  } finally {
    clearTimeout(connectTimer);
  }

  const response = new NextResponse(upstream.body, {
    status: upstream.status,
    headers: eventStreamHeaders(upstream.headers, requestId),
  });
  if (upstream.status === 401 && token) {
    clearSessionCookie(response);
  }
  return response;
}
