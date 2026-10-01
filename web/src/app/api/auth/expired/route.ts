/**
 * GET /api/auth/expired?next=/path — Server Components send the browser here
 * when the API rejects the session (they cannot change cookies themselves).
 *
 * Any site can link here, so the cookie is dropped only when the API itself
 * rejects the session now: a session the API still accepts (a cross-site link
 * to this route) is kept and the browser goes straight to `next`. An
 * unreachable API signs nobody out either.
 */

import { NextResponse, type NextRequest } from "next/server";

import { LOCALE_COOKIE, matchLocale } from "@/i18n/config";
import { HOME_PATH, loginPath, safeNextPath } from "@/lib/navigation";
import { SESSION_COOKIE, buildUpstreamHeaders, callBackend, sanitizeRequestId } from "@/server/backend";
import { clearSessionCookie } from "@/server/relay";

export const dynamic = "force-dynamic";

const SESSION_CHECK_TIMEOUT_MS = 5_000;

async function isSessionRejected(token: string, request: NextRequest): Promise<boolean> {
  try {
    const response = await callBackend("/v1/me", {
      headers: buildUpstreamHeaders(null, {
        token,
        locale: matchLocale(request.cookies.get(LOCALE_COOKIE)?.value),
        requestId: sanitizeRequestId(null),
      }),
      timeoutMs: SESSION_CHECK_TIMEOUT_MS,
    });
    return response.status === 401;
  } catch {
    return false;
  }
}

export async function GET(request: NextRequest): Promise<Response> {
  const next = request.nextUrl.searchParams.get("next");
  const token = request.cookies.get(SESSION_COOKIE)?.value;
  if (token && !(await isSessionRejected(token, request))) {
    // The API returns 401 only for a missing or rejected session, so going
    // back to `next` cannot loop here.
    return NextResponse.redirect(new URL(safeNextPath(next, HOME_PATH), request.url));
  }
  const response = NextResponse.redirect(new URL(loginPath({ next, reason: "expired" }), request.url));
  if (token) {
    clearSessionCookie(response);
  }
  return response;
}
