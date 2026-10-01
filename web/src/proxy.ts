/**
 * Runs before every page (not /api, not static files):
 *  - a plain form POST (the payment page's return) becomes a GET (303);
 *  - visitors without a session go to /login?next=<page>;
 *  - signed-in users opening /login go to their businesses;
 *  - Server Components learn the current path (for "back after sign-in");
 *  - a signed-in user without a language cookie gets the account language.
 */

import { NextResponse, type NextRequest } from "next/server";

import { LOCALE_COOKIE, matchLocale, negotiateLocale, DEFAULT_LOCALE } from "@/i18n/config";
import { HOME_PATH, LOGIN_PATH, isProtectedPath, loginPath, safeNextPath } from "@/lib/navigation";
import {
  PATHNAME_HEADER,
  SESSION_COOKIE,
  buildUpstreamHeaders,
  callBackend,
  localeCookieOptions,
  sanitizeRequestId,
} from "@/server/backend";

const LOCALE_LOOKUP_TIMEOUT_MS = 3_000;

async function accountLocale(token: string): Promise<string | null> {
  try {
    const response = await callBackend("/v1/me", {
      headers: buildUpstreamHeaders(null, { token, requestId: sanitizeRequestId(null) }),
      timeoutMs: LOCALE_LOOKUP_TIMEOUT_MS,
    });
    if (!response.ok) {
      return null;
    }
    const me = (await response.json()) as { user?: { locale?: string } };
    return me.user?.locale ?? null;
  } catch {
    return null;
  }
}

export async function proxy(request: NextRequest): Promise<NextResponse> {
  const { pathname, search, searchParams } = request.nextUrl;
  const token = request.cookies.get(SESSION_COOKIE)?.value;

  // The payment page (Flitt) returns the payer with a cross-site form POST,
  // which never carries the SameSite=Lax session cookie. Pages take no plain
  // POSTs (Server Actions send Next-Action), so answer 303: the browser
  // repeats the visit as a GET, which does carry the cookie.
  if (request.method === "POST" && !request.headers.has("next-action")) {
    return NextResponse.redirect(new URL(`${pathname}${search}`, request.url), 303);
  }

  if (!token && isProtectedPath(pathname)) {
    return NextResponse.redirect(new URL(loginPath({ next: `${pathname}${search}` }), request.url));
  }
  if (token && pathname === LOGIN_PATH && !searchParams.has("reason")) {
    return NextResponse.redirect(new URL(safeNextPath(searchParams.get("next"), HOME_PATH), request.url));
  }

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set(PATHNAME_HEADER, `${pathname}${search}`);

  let newLocale: string | null = null;
  if (token && !request.cookies.has(LOCALE_COOKIE)) {
    newLocale =
      matchLocale(await accountLocale(token)) ??
      negotiateLocale(request.headers.get("accept-language")) ??
      DEFAULT_LOCALE;
    request.cookies.set(LOCALE_COOKIE, newLocale);
    requestHeaders.set("cookie", request.cookies.toString());
  }

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  if (newLocale) {
    response.cookies.set(LOCALE_COOKIE, newLocale, localeCookieOptions());
  }
  return response;
}

export const config = {
  matcher: ["/((?!api/|_next/|favicon\\.ico|icon\\.svg|robots\\.txt|.*\\.[a-zA-Z0-9]+$).*)"],
};
