/**
 * The first-touch attribution cookie (lib/attribution.ts) on the server:
 * the proxy sets it on a visitor's first landing or hosted chat page, the
 * BFF's sign-in route sends it to the API and drops it. httpOnly (page
 * scripts never read it), SameSite=Lax, Secure over HTTPS, 90 days.
 */

import type { NextRequest, NextResponse } from "next/server";

import {
  ATTRIBUTION_COOKIE,
  ATTRIBUTION_MAX_AGE_SECONDS,
  attributionOfVisit,
  decodeAttribution,
  encodeAttribution,
  isAttributionPage,
} from "@/lib/attribution";

import { isCookieSecure } from "./backend";
import { readSessionToken } from "./sessionCookie";

const REDIRECT_MIN_STATUS = 300;

function attributionCookieOptions() {
  return {
    httpOnly: true,
    secure: isCookieSecure(),
    sameSite: "lax" as const,
    path: "/",
    maxAge: ATTRIBUTION_MAX_AGE_SECONDS,
  };
}

/**
 * Remember where a visitor without a session first came from, on the page
 * they arrived at; a visitor who already has the cookie keeps the first.
 */
export function rememberFirstVisit(request: NextRequest, response: NextResponse, nowMs: number = Date.now()): void {
  if (
    request.method !== "GET" ||
    response.status >= REDIRECT_MIN_STATUS ||
    !isAttributionPage(request.nextUrl.pathname) ||
    request.cookies.has(ATTRIBUTION_COOKIE) ||
    readSessionToken(request.cookies)
  ) {
    return;
  }
  const attribution = attributionOfVisit(request.nextUrl, request.headers.get("referer"), nowMs);
  response.cookies.set(ATTRIBUTION_COOKIE, encodeAttribution(attribution), attributionCookieOptions());
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

/** After a successful sign-in the first touch has done its work. */
export function forgetAttribution(response: NextResponse): void {
  response.cookies.set(ATTRIBUTION_COOKIE, "", { ...attributionCookieOptions(), maxAge: 0 });
}

export function readAttributionCookie(request: NextRequest): string | undefined {
  return request.cookies.get(ATTRIBUTION_COOKIE)?.value;
}
