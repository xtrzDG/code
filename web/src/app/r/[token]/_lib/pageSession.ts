/**
 * The booking page's short-lived credential. The link in the guest's
 * confirmation carries a long-lived token; once the page has opened, it
 * trades it for a credential of about 30 minutes
 * (POST /v1/public/bookings/{token}/session) and takes the token out of
 * the address bar: the address becomes `/r/booking`, and the credential
 * stays in this tab only (sessionStorage), so a reload of the tab still
 * opens the booking. The link itself keeps working: opening it again
 * starts over.
 */

import { api } from "@/api/client";
import { unwrap } from "@/api/result";
import type { BookingProblem } from "@/lib/bookingPage/refusals";

import { PAGE_SESSION_PATH } from "./pageSessionPath";

const STORAGE_KEY = "aw_booking_page";

export interface PageSession {
  /** The credential: every route of the page takes it in place of the link's token. */
  token: string;
  /** When it stops opening the booking (microseconds). */
  expiresAt: number;
  /** The guest's language, for a page that cannot open the booking any more. */
  language: string;
}

/** Trade the link's token for the page's credential. */
export async function openPageSession(linkToken: string, language: string): Promise<PageSession> {
  const session = await unwrap(api.POST("/v1/public/bookings/{token}/session", { params: { path: { token: linkToken } } }));
  return { token: session.token, expiresAt: session.expires_at, language };
}

/** Keep the credential for this tab; false when the browser keeps nothing (then the link stays). */
export function storePageSession(session: PageSession): boolean {
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    return true;
  } catch {
    return false;
  }
}

/** The credential of this tab while it still opens the booking, else null. */
export function readPageSession(nowMicroseconds: number = Date.now() * 1000): PageSession | null {
  let stored: unknown;
  try {
    stored = JSON.parse(window.sessionStorage.getItem(STORAGE_KEY) ?? "null");
  } catch {
    return null;
  }
  if (!isPageSession(stored) || stored.expiresAt <= nowMicroseconds) {
    return null;
  }
  return stored;
}

/** The language the tab's last booking page spoke (also once its credential ended). */
export function lastPageLanguage(): string | null {
  try {
    const stored: unknown = JSON.parse(window.sessionStorage.getItem(STORAGE_KEY) ?? "null");
    return isPageSession(stored) ? stored.language : null;
  } catch {
    return null;
  }
}

/** A problem of the page: the API's, or `pageClosed` once the page's credential ended. */
export type PageProblem = BookingProblem | "pageClosed";

/**
 * What the guest reads about a refusal: on the page's credential an
 * expired or refused one only closes this page (the link in their
 * confirmation still opens the booking), so it says so instead of
 * calling their link expired or invalid.
 */
export function pageProblemOf(failure: BookingProblem, isSession: boolean): PageProblem {
  return isSession && (failure === "linkExpired" || failure === "linkInvalid") ? "pageClosed" : failure;
}

/** The address bar without the link's token (the page's history entry is replaced). */
export function hideLinkToken(): void {
  window.history.replaceState(null, "", PAGE_SESSION_PATH);
}

function isPageSession(value: unknown): value is PageSession {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.token === "string" &&
    typeof candidate.expiresAt === "number" &&
    typeof candidate.language === "string"
  );
}
