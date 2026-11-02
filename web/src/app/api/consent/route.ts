/**
 * POST /api/consent {"choice": "granted" | "denied", "page", "referrer"} —
 * the visitor's answer on the public site's cookie banner
 * (components/consent): stored in the technical `aw_consent` cookie for
 * six months (server/consentCookie.ts). Accepting also keeps where the
 * visitor came from (`aw_attr`) unless they have it already or are signed
 * in: the public page their visit began on (`page`, its path and query)
 * and another site's page before it (`referrer`), checked like the
 * proxy's first visit (components/consent/saveConsent.ts sends them).
 * Rejecting drops `aw_attr`. Every answer is logged on the server with
 * its pseudonymous receipt id, kept in the cookie so a changed mind keeps
 * one history (server/consentLog.ts). Answers 204; 403 for another site
 * (no site may answer for the visitor), 413 over 4 KB, 422 for anything
 * but a choice.
 */

import { NextResponse, type NextRequest } from "next/server";

import { ATTRIBUTION_COOKIE, attributionOfVisit, isAttributionPage } from "@/lib/attribution";
import { z } from "@/lib/zod";
import { forgetAttribution, keepAttribution } from "@/server/attributionCookie";
import { REQUEST_ID_HEADER, jsonError, sanitizeRequestId } from "@/server/backend";
import { BodyTooLargeError, readLimitedText } from "@/server/bodyLimits";
import { CONSENT_VERSION, newConsentId, readConsentId, setConsentCookie } from "@/server/consentCookie";
import { logConsent } from "@/server/consentLog";
import { isSameOriginRequest } from "@/server/sameOrigin";
import { readSessionToken } from "@/server/sessionCookie";

export const dynamic = "force-dynamic";

const CONSENT_BODY_LIMIT_BYTES = 4 * 1024;

const ConsentAnswer = z.object({
  choice: z.enum(["granted", "denied"]),
  page: z.string().max(2048).optional(),
  referrer: z.string().max(2048).optional(),
});

function parseJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

/** The page of this site the visit began on; null for anything else. */
function acceptedOn(page: string | undefined, request: NextRequest): URL | null {
  if (!page?.startsWith("/") || page.startsWith("//")) {
    return null;
  }
  try {
    const url = new URL(page, request.nextUrl.origin);
    return url.origin === request.nextUrl.origin && isAttributionPage(url.pathname) ? url : null;
  } catch {
    return null;
  }
}

export async function POST(request: NextRequest): Promise<Response> {
  const requestId = sanitizeRequestId(request.headers.get(REQUEST_ID_HEADER));
  if (!isSameOriginRequest(request.headers)) {
    return jsonError(403, "forbidden_origin", "Cross-site request refused.", requestId);
  }
  let body: string;
  try {
    body = await readLimitedText(request, CONSENT_BODY_LIMIT_BYTES);
  } catch (error) {
    if (error instanceof BodyTooLargeError) {
      return jsonError(413, "payload_too_large", error.message, requestId);
    }
    throw error;
  }
  const parsed = ConsentAnswer.safeParse(parseJson(body));
  if (!parsed.success) {
    return jsonError(422, "validation_failed", "Unknown cookie choice.", requestId);
  }

  const { choice, page, referrer } = parsed.data;
  const response = new NextResponse(null, { status: 204, headers: { "cache-control": "no-store" } });
  const consentId = readConsentId(request.cookies) ?? newConsentId();
  setConsentCookie(response, choice, consentId, request.headers);
  logConsent({ choice, version: CONSENT_VERSION, consentId, at: new Date().toISOString() });
  if (choice === "denied") {
    if (request.cookies.has(ATTRIBUTION_COOKIE)) {
      forgetAttribution(response, request.headers);
    }
    return response;
  }
  const visit = acceptedOn(page, request);
  if (visit !== null && !request.cookies.has(ATTRIBUTION_COOKIE) && !readSessionToken(request.cookies, request.headers)) {
    keepAttribution(response, attributionOfVisit(visit, referrer ?? null, Date.now()), request.headers);
  }
  return response;
}
