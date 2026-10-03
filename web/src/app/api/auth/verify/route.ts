/**
 * POST /api/auth/verify — check the login code and open a session.
 *
 * Body: {"challenge_id", "code"} (at most 256 KB). On success the API's
 * bearer token goes into the httpOnly session cookie (`__Host-aw_session`
 * over HTTPS; never into the response body), the
 * interface language becomes the account's language, and the answer is
 * {"user", "is_new_user", "expires_at"}. Where the visitor first came from
 * (the `aw_attr` cookie) goes along as `signup_attribution` and the cookie
 * is dropped once signed in.
 */

import { NextResponse, type NextRequest } from "next/server";

import type { LoginSessionView } from "@/api/types";
import { LOCALE_COOKIE, matchLocale } from "@/i18n/config";
import {
  callBackend,
  dateFromMicroseconds,
  jsonError,
  localeCookieOptions,
  pickResponseHeaders,
} from "@/server/backend";
import { forgetAttribution, readAttributionCookie, withSignupAttribution } from "@/server/attributionCookie";
import { BodyTooLargeError, DEFAULT_BODY_LIMIT_BYTES, readLimitedText } from "@/server/bodyLimits";
import { prepareBackendCall } from "@/server/relay";
import { setSessionCookie } from "@/server/sessionCookie";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest): Promise<Response> {
  const prepared = prepareBackendCall(request, { useSession: false });
  if ("refusal" in prepared) {
    return prepared.refusal;
  }
  const { requestId, headers } = prepared;

  let body: string;
  try {
    body = await readLimitedText(request, DEFAULT_BODY_LIMIT_BYTES);
  } catch (error) {
    if (error instanceof BodyTooLargeError) {
      return jsonError(413, "payload_too_large", error.message, requestId);
    }
    throw error;
  }

  let upstream: Response;
  try {
    upstream = await callBackend("/v1/auth/otp/verify", {
      method: "POST",
      headers,
      body: withSignupAttribution(body, readAttributionCookie(request)),
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
  setSessionCookie(response, session.access_token, dateFromMicroseconds(session.expires_at));
  forgetAttribution(response);
  const accountLocale = matchLocale(session.user.locale);
  if (accountLocale) {
    response.cookies.set(LOCALE_COOKIE, accountLocale, localeCookieOptions());
  }
  return response;
}
