/**
 * POST /api/auth/verify — check the login code and open a session.
 *
 * Body: {"challenge_id", "code"} (at most 256 KB). On success the API's
 * bearer token goes into the httpOnly session cookie (`__Host-aw_session`
 * over HTTPS; never into the response body), the
 * interface language becomes the account's language, and the answer is
 * {"user", "is_new_user", "expires_at", "auth_level", "recovery_codes"}
 * (src/server/sessionOpening.ts). People with an authenticator app (and
 * every platform admin) get no session yet: the answer is the second step,
 * {"mfa_required": true, "mfa_challenge", "is_new_user"}, finished by
 * POST /api/auth/mfa/verify. Where the visitor first came from (the
 * `aw_attr` cookie) goes along as `signup_attribution`.
 */

import { NextResponse, type NextRequest } from "next/server";

import type { LoginSessionView, MfaRequiredView } from "@/api/types";
import { callBackend, jsonError, pickResponseHeaders } from "@/server/backend";
import {
  readAttributionCookie,
  withSignupAttribution,
} from "@/server/attributionCookie";
import {
  BodyTooLargeError,
  DEFAULT_BODY_LIMIT_BYTES,
  readLimitedText,
} from "@/server/bodyLimits";
import { prepareBackendCall } from "@/server/relay";
import { openSession } from "@/server/sessionOpening";

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
    return jsonError(
      502,
      "backend_unavailable",
      "The API is not reachable.",
      requestId,
    );
  }

  if (!upstream.ok) {
    return new NextResponse(upstream.body, {
      status: upstream.status,
      headers: pickResponseHeaders(upstream.headers, requestId),
    });
  }

  const answer = (await upstream.json()) as LoginSessionView | MfaRequiredView;
  if ("mfa_required" in answer && answer.mfa_required) {
    return NextResponse.json(
      {
        mfa_required: true,
        mfa_challenge: answer.mfa_challenge,
        is_new_user: answer.is_new_user,
      },
      { headers: pickResponseHeaders(upstream.headers, requestId) },
    );
  }
  return openSession(answer as LoginSessionView, upstream.headers, requestId);
}
