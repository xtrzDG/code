/**
 * The visitor's cookie choice on the public site (ePrivacy art. 5(3), the
 * Italian Garante's cookie guidelines of 10 June 2021): `aw_consent`, a
 * technical cookie that needs no consent itself. It holds the choice only
 * ("1.granted" or "1.denied": the version of the question, then the
 * answer), for six months; then, or when the version changes because the
 * cookies asked about change, the banner asks again. Accepting lets the
 * proxy keep where the visitor first came from (`aw_attr`,
 * attributionCookie.ts); rejecting, closing the banner or not answering
 * keeps nothing, and a later rejection drops what was kept.
 */

import type { NextResponse } from "next/server";

import { isCookieSecure, type HeaderReader } from "./cookieSecurity";

export const CONSENT_COOKIE = "aw_consent";
/** Six months (183 days): the Garante's guidelines ask not to show the banner again sooner. */
export const CONSENT_MAX_AGE_SECONDS = 183 * 24 * 60 * 60;
/** Raise it when the cookies the banner asks about change: every stored answer is then asked again. */
const CONSENT_VERSION = "1";

export type ConsentChoice = "granted" | "denied";

interface CookieReader {
  get(name: string): { value: string } | undefined;
}

/** The stored answer, or null: none yet, or one to an older question. */
export function parseConsent(value: string | undefined): ConsentChoice | null {
  if (value === `${CONSENT_VERSION}.granted`) {
    return "granted";
  }
  if (value === `${CONSENT_VERSION}.denied`) {
    return "denied";
  }
  return null;
}

export function readConsent(cookies: CookieReader): ConsentChoice | null {
  return parseConsent(cookies.get(CONSENT_COOKIE)?.value);
}

/** The visitor accepted the attribution cookie. */
export function hasAttributionConsent(cookies: CookieReader): boolean {
  return readConsent(cookies) === "granted";
}

export function setConsentCookie(response: NextResponse, choice: ConsentChoice, headers: HeaderReader | null): void {
  response.cookies.set(CONSENT_COOKIE, `${CONSENT_VERSION}.${choice}`, {
    httpOnly: true,
    secure: isCookieSecure(headers),
    sameSite: "lax",
    path: "/",
    maxAge: CONSENT_MAX_AGE_SECONDS,
  });
}
