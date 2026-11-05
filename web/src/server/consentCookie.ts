/**
 * The visitor's cookie choice on the public site (ePrivacy art. 5(3), the
 * Italian Garante's cookie guidelines of 10 June 2021): `aw_consent`, a
 * technical cookie that needs no consent itself. It holds the choice
 * ("1.granted" or "1.denied": the version of the question, then the
 * answer) and the answer's pseudonymous receipt id, which the server's
 * consent log names too (consentLog.ts), for six months; then, or when
 * the version changes because the cookies asked about change, the banner
 * asks again. An answer stored before receipts ("1.granted") still counts.
 * Accepting lets the proxy keep where the visitor first came from (`aw_attr`,
 * attributionCookie.ts); rejecting, closing the banner or not answering
 * keeps nothing, and a later rejection drops what was kept.
 */

import type { NextResponse } from "next/server";

import { isCookieSecure, type HeaderReader } from "./cookieSecurity";

export const CONSENT_COOKIE = "aw_consent";
/** Six months (183 days): the Garante's guidelines ask not to show the banner again sooner. */
export const CONSENT_MAX_AGE_SECONDS = 183 * 24 * 60 * 60;
/** Raise it when the cookies the banner asks about change: every stored answer is then asked again. */
export const CONSENT_VERSION = "1";
/** A receipt id: 16 random bytes, base64url without padding. */
const CONSENT_ID_PATTERN = /^[A-Za-z0-9_-]{22}$/;
const CONSENT_ID_BYTES = 16;

export type ConsentChoice = "granted" | "denied";

interface CookieReader {
  get(name: string): { value: string } | undefined;
}

interface StoredConsent {
  choice: ConsentChoice;
  consentId: string | null;
}

/** "1.granted.<id>" (or "1.granted" from before receipts); null for anything else. */
function readStored(value: string | undefined): StoredConsent | null {
  const [version, answer, consentId, ...rest] = (value ?? "").split(".");
  const choice: ConsentChoice | null = answer === "granted" || answer === "denied" ? answer : null;
  const isId = consentId === undefined || CONSENT_ID_PATTERN.test(consentId);
  if (version !== CONSENT_VERSION || choice === null || !isId || rest.length > 0) {
    return null;
  }
  return { choice, consentId: consentId ?? null };
}

/** The stored answer, or null: none yet, or one to an older question. */
export function parseConsent(value: string | undefined): ConsentChoice | null {
  return readStored(value)?.choice ?? null;
}

export function readConsent(cookies: CookieReader): ConsentChoice | null {
  return parseConsent(cookies.get(CONSENT_COOKIE)?.value);
}

/** The receipt id of the visitor's stored answer, so a changed mind keeps its history; null without one. */
export function readConsentId(cookies: CookieReader): string | null {
  return readStored(cookies.get(CONSENT_COOKIE)?.value)?.consentId ?? null;
}

/** A new pseudonymous receipt id: random, so it says nothing about the visitor. */
export function newConsentId(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(CONSENT_ID_BYTES));
  return btoa(String.fromCharCode(...bytes)).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/, "");
}

/** The visitor accepted the attribution cookie. */
export function hasAttributionConsent(cookies: CookieReader): boolean {
  return readConsent(cookies) === "granted";
}

export function setConsentCookie(
  response: NextResponse,
  choice: ConsentChoice,
  consentId: string,
  headers: HeaderReader | null,
): void {
  response.cookies.set(CONSENT_COOKIE, `${CONSENT_VERSION}.${choice}.${consentId}`, {
    httpOnly: true,
    secure: isCookieSecure(headers),
    sameSite: "lax",
    path: "/",
    maxAge: CONSENT_MAX_AGE_SECONDS,
  });
}
