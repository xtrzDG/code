/**
 * Sentry envelopes passing through the cabinet's tunnel: the browser's
 * envelope is readdressed to the configured project and forwarded.
 */

export const MAX_ENVELOPE_BYTES = 256 * 1024;

export interface ParsedDsn {
  origin: string;
  projectId: string;
}

export function parseDsn(dsn: string): ParsedDsn | null {
  try {
    const url = new URL(dsn);
    const projectId = url.pathname.split("/").filter(Boolean).at(-1) ?? "";
    if (!/^https?:$/.test(url.protocol) || !url.username || !/^\d+$/.test(projectId)) {
      return null;
    }
    return { origin: url.origin, projectId };
  } catch {
    return null;
  }
}

/** Where Sentry accepts envelopes of the project. */
export function envelopeUrl(dsn: ParsedDsn): string {
  return `${dsn.origin}/api/${dsn.projectId}/envelope/`;
}

/** The envelope with the configured DSN in its header; null when it is not one. */
export function readdressEnvelope(body: string, dsn: string): string | null {
  const newline = body.indexOf("\n");
  if (newline <= 0) {
    return null;
  }
  try {
    const header = JSON.parse(body.slice(0, newline)) as unknown;
    if (typeof header !== "object" || header === null || Array.isArray(header)) {
      return null;
    }
    return `${JSON.stringify({ ...header, dsn })}${body.slice(newline)}`;
  } catch {
    return null;
  }
}

/** A fixed window counter: at most `limit` events per `windowMs` (per process). */
export function createWindowLimiter(limit: number, windowMs: number, now: () => number = Date.now) {
  let windowStart = now();
  let count = 0;
  return function tryAcquire(): boolean {
    const current = now();
    if (current - windowStart >= windowMs) {
      windowStart = current;
      count = 0;
    }
    if (count >= limit) {
      return false;
    }
    count += 1;
    return true;
  };
}
