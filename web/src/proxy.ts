/**
 * Runs before every page (not /api, not static files):
 *  - a plain form POST (the payment page's return) becomes a GET (303);
 *  - visitors without a session go to /login?next=<page>;
 *  - signed-in users opening /login go to their businesses;
 *  - Server Components learn the current path (for "back after sign-in");
 *  - a signed-in user without a language cookie gets the account language;
 *  - every page gets a Content Security Policy with a fresh nonce, which
 *    Next.js puts on its own scripts (server/contentSecurityPolicy.ts);
 *  - a session under the cookie's old name moves to `__Host-aw_session`;
 *  - the public hosted chat page (/c/{address}) gets its business and a
 *    stricter policy (server/hostedChatProxy.ts); no /c/ page is indexed.
 */

import { NextResponse, type NextRequest } from "next/server";

import { LOCALE_COOKIE, matchLocale, negotiateLocale, DEFAULT_LOCALE } from "@/i18n/config";
import { HOME_PATH, LOGIN_PATH, isProtectedPath, loginPath, safeNextPath } from "@/lib/navigation";
import {
  PATHNAME_HEADER,
  buildUpstreamHeaders,
  callBackend,
  isCookieSecure,
  localeCookieOptions,
  sanitizeRequestId,
} from "@/server/backend";
import { NONCE_HEADER, buildContentSecurityPolicy, createNonce } from "@/server/contentSecurityPolicy";
import { HOSTED_CHAT_HEADER, hostedChatAddress, isHostedChatPath } from "@/server/hostedChat";
import { NOINDEX, ROBOTS_HEADER, routeHostedChat } from "@/server/hostedChatProxy";
import { migrateLegacySessionCookie, readSessionToken } from "@/server/sessionCookie";

const CSP_HEADER = "content-security-policy";

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
  const response = await route(request);
  migrateLegacySessionCookie(request, response);
  return response;
}

async function route(request: NextRequest): Promise<NextResponse> {
  const { pathname, search, searchParams } = request.nextUrl;
  const token = readSessionToken(request.cookies);

  // The payment page (Flitt) returns the payer with a cross-site form POST,
  // which never carries the SameSite=Lax session cookie. Pages take no plain
  // POSTs (Server Actions send Next-Action), so answer 303: the browser
  // repeats the visit as a GET, which does carry the cookie.
  if (request.method === "POST" && !request.headers.has("next-action")) {
    return NextResponse.redirect(new URL(`${pathname}${search}`, request.url), 303);
  }

  const hostedChat = hostedChatAddress(pathname);
  if (hostedChat !== null) {
    return routeHostedChat(request, hostedChat);
  }

  if (!token && isProtectedPath(pathname)) {
    return NextResponse.redirect(new URL(loginPath({ next: `${pathname}${search}` }), request.url));
  }
  if (token && pathname === LOGIN_PATH && !searchParams.has("reason")) {
    return NextResponse.redirect(new URL(safeNextPath(searchParams.get("next"), HOME_PATH), request.url));
  }

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set(PATHNAME_HEADER, `${pathname}${search}`);
  // Next.js reads the nonce from the request's policy while rendering.
  const nonce = createNonce();
  const policy = buildContentSecurityPolicy({
    nonce,
    isDevelopment: process.env.NODE_ENV === "development",
    isHttps: isCookieSecure(),
  });
  requestHeaders.set(CSP_HEADER, policy);
  requestHeaders.set(NONCE_HEADER, nonce);
  // Only the proxy says which business a hosted chat page shows.
  requestHeaders.delete(HOSTED_CHAT_HEADER);

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
  response.headers.set(CSP_HEADER, policy);
  if (isHostedChatPath(pathname)) {
    response.headers.set(ROBOTS_HEADER, NOINDEX);
  }
  if (newLocale) {
    response.cookies.set(LOCALE_COOKIE, newLocale, localeCookieOptions());
  }
  return response;
}

export const config = {
  matcher: ["/((?!api/|_next/|favicon\\.ico|icon\\.svg|robots\\.txt|.*\\.[a-zA-Z0-9]+$).*)"],
};
