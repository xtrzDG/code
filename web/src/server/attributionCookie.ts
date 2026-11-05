/**
 * The first-touch attribution cookie (lib/attribution.ts) on the server:
 * kept only with the visitor's consent (`aw_consent`, consentCookie.ts):
 * the proxy sets it on a visitor's first landing or hosted chat page once
 * they accepted it, the consent route (POST /api/consent) when they accept
 * it, and the BFF's sign-in route sends it to the API and drops it.
 * Without consent it is never set, and one already there (from before the
 * banner, or a consent taken back) is dropped. httpOnly (page scripts never
 * read it), SameSite=Lax, Secure over HTTPS, 90 days.
 */

import type { NextRequest, NextResponse } from "next/server";

import {
  ATTRIBUTION_COOKIE,
  ATTRIBUTION_MAX_AGE_SECONDS,
  attributionOfVisit,
  decodeAttribution,
  encodeAttribution,
  isAttributionPage,
  type SignupAttribution,
} from "@/lib/attribution";

import { hasAttributionConsent } from "./consentCookie";
import { isCookieSecure, type HeaderReader } from "./cookieSecurity";
import { readSessionToken } from "./sessionCookie";

const REDIRECT_MIN_STATUS = 300;

function attributionCookieOptions(headers: HeaderReader | null) {
  return {
    httpOnly: true,
    secure: isCookieSecure(headers),
    sameSite: "lax" as const,
    path: "/",
    maxAge: ATTRIBUTION_MAX_AGE_SECONDS,
  };
}

/**
 * Remember where a visitor without a session first came from, on the page
 * they arrived at, once they accepted it; a visitor who already has the
 * cookie keeps the first. Without consent a cookie already there is dropped.
 */
export function rememberFirstVisit(request: NextRequest, response: NextResponse, nowMs: number = Date.now()): void {
  if (!hasAttributionConsent(request.cookies)) {
    if (request.cookies.has(ATTRIBUTION_COOKIE)) {
      forgetAttribution(response, request.headers);
    }
    return;
  }
  if (
    request.method !== "GET" ||
    response.status >= REDIRECT_MIN_STATUS ||
    !isAttributionPage(request.nextUrl.pathname) ||
    request.cookies.has(ATTRIBUTION_COOKIE) ||
    readSessionToken(request.cookies, request.headers)
  ) {
    return;
  }
  keepAttribution(response, attributionOfVisit(request.nextUrl, request.headers.get("referer"), nowMs), request.headers);
}

/** Store where a visitor came from (the visit's attribution, already checked). */
export function keepAttribution(response: NextResponse, attribution: SignupAttribution, headers: HeaderReader | null): void {
  response.cookies.set(ATTRIBUTION_COOKIE, encodeAttribution(attribution), attributionCookieOptions(headers));
}

/**
 * The sign-in body with the cookie's attribution as `signup_attribution`
 * (the API keeps it only when the sign-in creates the account). Whatever
 * the browser put there itself is replaced: only the cookie counts. A body
 * that is not a JSON object goes on unchanged (the API answers 422).
 */
export function withSignupAttribution(body: string, cookieValue: string | undefined): string {
  let parsed: unknown;
  try {
    parsed = JSON.parse(body);
  } catch {
    return body;
  }
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    return body;
  }
  const { signup_attribution: _ignored, ...rest } = parsed as Record<string, unknown>;
  const attribution = decodeAttribution(cookieValue);
  return JSON.stringify(attribution === null ? rest : { ...rest, signup_attribution: attribution });
}

/** After a successful sign-in the first touch has done its work; without consent it goes too. */
export function forgetAttribution(response: NextResponse, headers: HeaderReader | null): void {
  response.cookies.set(ATTRIBUTION_COOKIE, "", { ...attributionCookieOptions(headers), maxAge: 0 });
}

/** The cookie's value, only while the visitor's consent stands. */
export function readAttributionCookie(request: NextRequest): string | undefined {
  return hasAttributionConsent(request.cookies) ? request.cookies.get(ATTRIBUTION_COOKIE)?.value : undefined;
}
