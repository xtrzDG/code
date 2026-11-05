/**
 * The Sentry tunnel of the cabinet: browser error envelopes arrive here
 * (same origin, so no CSP or ad blocker stands in the way) and go to the
 * project of SENTRY_DSN. Without SENTRY_DSN they are dropped. Only the
 * site's own pages may send (server/sameOrigin.ts), an envelope over
 * MAX_ENVELOPE_BYTES is refused before it is read in full, and at most
 * TUNNEL_ENVELOPES_PER_MINUTE envelopes per server process are forwarded,
 * so nobody can spend the project's quota through it.
 */

import { createWindowLimiter, envelopeUrl, MAX_ENVELOPE_BYTES, parseDsn, readdressEnvelope } from "@/lib/monitoring/envelope";
import { readDsn } from "@/lib/monitoring/options";
import { BodyTooLargeError, readLimitedText } from "@/server/bodyLimits";
import { isSameOriginRequest } from "@/server/sameOrigin";

const TUNNEL_ENVELOPES_PER_MINUTE = 120;
const FORWARD_TIMEOUT_MS = 5_000;
const tryAcquire = createWindowLimiter(TUNNEL_ENVELOPES_PER_MINUTE, 60_000);

function noContent(status = 204): Response {
  return new Response(null, { status });
}

export async function POST(request: Request): Promise<Response> {
  if (!isSameOriginRequest(request.headers)) {
    return noContent(403);
  }
  const env = process.env;
  const dsn = readDsn(env);
  const target = dsn === null ? null : parseDsn(dsn);
  if (dsn === null || target === null) {
    return noContent();
  }
  let body: string;
  try {
    body = await readLimitedText(request, MAX_ENVELOPE_BYTES);
  } catch (error) {
    if (error instanceof BodyTooLargeError) {
      return noContent(413);
    }
    throw error;
  }
  const envelope = readdressEnvelope(body, dsn);
  if (envelope === null) {
    return noContent(400);
  }
  if (!tryAcquire()) {
    return noContent(429);
  }
  try {
    await fetch(envelopeUrl(target), {
      method: "POST",
      headers: { "Content-Type": "application/x-sentry-envelope" },
      body: envelope,
      signal: AbortSignal.timeout(FORWARD_TIMEOUT_MS),
    });
  } catch {
    // Sentry unreachable: the error is lost, the page is not affected.
  }
  return noContent();
}
