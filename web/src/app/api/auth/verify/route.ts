/**
 * POST /api/auth/verify — check the login code and open a session.
 *
 * Body: {"challenge_id", "code"}. On success the API's bearer token goes
 * into the httpOnly session cookie (never into the response body), the
 * interface language becomes the account's language, and the answer is
 * {"user", "is_new_user", "expires_at"}.
 */

import { NextResponse, type NextRequest } from "next/server";

import type { LoginSessionView } from "@/api/types";
import { LOCALE_COOKIE, matchLocale } from "@/i18n/config";
import {
  SESSION_COOKIE,
  callBackend,
  dateFromMicroseconds,
  jsonError,
  localeCookieOptions,
  pickResponseHeaders,
  sessionCookieOptions,
} from "@/server/backend";
import { prepareBackendCall } from "@/server/relay";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest): Promise<Response> {
  const prepared = prepareBackendCall(request, { useSession: false });
  if ("refusal" in prepared) {
    return prepared.refusal;
  }
  const { requestId, headers } = prepared;

  let upstream: Response;
  try {
    upstream = await callBackend("/v1/auth/otp/verify", {
      method: "POST",
      headers,
      body: await request.text(),
    });
  } catch {
    return jsonError(502, "backend_unavailable", "The API is not reachable.", requestId);
  }

  if (!upstream.ok) {
    return new NextResponse(upstream.body, {
      status: upstream.status,
      headers: pickResponseHeaders(upstream.headers, requestId),
    });
  }

  const session = (await upstream.json()) as LoginSessionView;
  const response = NextResponse.json(
    { user: session.user, is_new_user: session.is_new_user, expires_at: session.expires_at },
    { headers: pickResponseHeaders(upstream.headers, requestId) },
  );
  response.cookies.set(
    SESSION_COOKIE,
    session.access_token,
    sessionCookieOptions(dateFromMicroseconds(session.expires_at)),
  );
  const accountLocale = matchLocale(session.user.locale);
  if (accountLocale) {
    response.cookies.set(LOCALE_COOKIE, accountLocale, localeCookieOptions());
  }
  return response;
}
