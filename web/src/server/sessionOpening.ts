import "server-only";

/**
 * Opening a session after a successful sign-in (the login code alone, or
 * its second step): the bearer token goes into the httpOnly session cookie,
 * never into the answer; the interface language becomes the account's;
 * the first-visit attribution cookie is dropped. The browser gets the
 * user, how the session is signed in and, right after an authenticator
 * was set up, its recovery codes (shown once).
 */

import { NextResponse } from "next/server";

import type { LoginSessionView } from "@/api/types";
import { LOCALE_COOKIE, matchLocale } from "@/i18n/config";

import { forgetAttribution } from "./attributionCookie";
import {
  dateFromMicroseconds,
  localeCookieOptions,
  pickResponseHeaders,
} from "./backend";
import { setSessionCookie } from "./sessionCookie";

export function openSession(
  session: LoginSessionView,
  upstreamHeaders: Headers,
  requestId: string,
): NextResponse {
  const response = NextResponse.json(
    {
      user: session.user,
      is_new_user: session.is_new_user,
      expires_at: session.expires_at,
      auth_level: session.auth_level ?? "one_factor",
      recovery_codes: session.recovery_codes ?? [],
    },
    { headers: pickResponseHeaders(upstreamHeaders, requestId) },
  );
  setSessionCookie(
    response,
    session.access_token,
    dateFromMicroseconds(session.expires_at),
  );
  forgetAttribution(response);
  const accountLocale = matchLocale(session.user.locale);
  if (accountLocale) {
    response.cookies.set(LOCALE_COOKIE, accountLocale, localeCookieOptions());
  }
  return response;
}
