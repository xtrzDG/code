/**
 * The Sentry tunnel of the cabinet: browser error envelopes arrive here
 * (same origin, so no CSP or ad blocker stands in the way) and go to the
 * project of SENTRY_DSN. Without SENTRY_DSN they are dropped. At most
 * TUNNEL_ENVELOPES_PER_MINUTE envelopes per server process are forwarded, so
 * nobody can spend the project's quota through it.
 */

import { createWindowLimiter, envelopeUrl, MAX_ENVELOPE_BYTES, parseDsn, readdressEnvelope } from "@/lib/monitoring/envelope";
import { readDsn } from "@/lib/monitoring/options";

const TUNNEL_ENVELOPES_PER_MINUTE = 120;
const FORWARD_TIMEOUT_MS = 5_000;
const tryAcquire = createWindowLimiter(TUNNEL_ENVELOPES_PER_MINUTE, 60_000);

function noContent(status = 204): Response {
  return new Response(null, { status });
}

export async function POST(request: Request): Promise<Response> {
  const env = process.env;
  const dsn = readDsn(env);
  const target = dsn === null ? null : parseDsn(dsn);
  if (dsn === null || target === null) {
    return noContent();
  }
  const body = await request.text();
  if (body.length > MAX_ENVELOPE_BYTES) {
    return noContent(413);
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
