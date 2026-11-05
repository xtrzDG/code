/**
 * `x-middleware-subrequest` is the header Next.js once used to mark its own
 * nested calls, and before 15.2.3 it skipped the middleware for any request
 * that carried it (CVE-2025-29927): a visitor could pass a protected page
 * without its sign-in redirect and Content Security Policy. The installed
 * Next.js no longer reads it (proxy.subrequest.test.ts checks the version);
 * the proxy still drops it from every request it forwards, so no page, route
 * handler or later framework code ever sees a value a browser wrote.
 *
 * Authorization never rests on the proxy anyway: the BFF forwards the
 * session and the API decides on every call (server/relay.ts).
 */

import type { NextRequest } from "next/server";

export const MIDDLEWARE_SUBREQUEST_HEADER = "x-middleware-subrequest";

/** The request's headers to forward, without the bypass header. */
export function forwardedRequestHeaders(request: NextRequest): Headers {
  const headers = new Headers(request.headers);
  headers.delete(MIDDLEWARE_SUBREQUEST_HEADER);
  return headers;
}
