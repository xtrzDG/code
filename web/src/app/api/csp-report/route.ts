/**
 * Content Security Policy violation reports of the cabinet's pages and the
 * hosted chat (`report-uri` and `report-to`, server/contentSecurityPolicy.ts).
 * A report is checked (type, size: MAX_CSP_REPORT_BYTES), counted (per
 * client and in all, per server process), cleaned of personal data
 * (server/cspReports.ts) and forwarded to Sentry's security endpoint of
 * SENTRY_DSN; without it, it is dropped. The browser never reads the
 * answer: 204 when accepted, 415, 413, 429 or 400 otherwise.
 */

import { createWindowLimiter } from "@/lib/monitoring/envelope";
import { BodyTooLargeError, isDeclaredTooLarge, readLimitedText } from "@/server/bodyLimits";
import {
  createKeyedWindowLimiter,
  reportClientKey,
  sentryCspReport,
  sentrySecurityUrl,
} from "@/server/cspReportForwarding";
import { isCspReportContentType, MAX_CSP_REPORT_BYTES, parseCspReports } from "@/server/cspReports";
import { siteOrigin } from "@/server/siteOrigin";

const REPORTS_PER_CLIENT_PER_MINUTE = 30;
const REPORTS_PER_MINUTE = 600;
const TRACKED_CLIENTS = 5_000;
const FORWARD_TIMEOUT_MS = 5_000;

const tryClient = createKeyedWindowLimiter(REPORTS_PER_CLIENT_PER_MINUTE, 60_000, TRACKED_CLIENTS);
const tryAny = createWindowLimiter(REPORTS_PER_MINUTE, 60_000);

function answer(status: number): Response {
  return new Response(null, { status });
}

export async function POST(request: Request): Promise<Response> {
  if (!isCspReportContentType(request.headers.get("content-type"))) {
    return answer(415);
  }
  if (isDeclaredTooLarge(request.headers, MAX_CSP_REPORT_BYTES)) {
    return answer(413);
  }
  if (!tryClient(reportClientKey(request.headers)) || !tryAny()) {
    return answer(429);
  }
  let body: string;
  try {
    body = await readLimitedText(request, MAX_CSP_REPORT_BYTES);
  } catch (error) {
    if (error instanceof BodyTooLargeError) {
      return answer(413);
    }
    throw error;
  }
  const violations = parseCspReports(body);
  if (violations === null) {
    return answer(400);
  }
  const target = sentrySecurityUrl(process.env);
  if (target !== null && violations.length > 0) {
    const origin = siteOrigin(request.headers);
    await Promise.allSettled(
      violations.map((violation) =>
        fetch(target, {
          method: "POST",
          headers: { "Content-Type": "application/csp-report" },
          body: sentryCspReport(violation, origin),
          signal: AbortSignal.timeout(FORWARD_TIMEOUT_MS),
        }),
      ),
    );
  }
  return answer(204);
}
