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
import { pickResponseHeaders } from "@/server/backend";
import {
  readAttributionCookie,
  withSignupAttribution,
} from "@/server/attributionCookie";
import { openSession } from "@/server/sessionOpening";
import { relaySignInStep } from "@/server/sessionOpeningRelay";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest): Promise<Response> {
  const step = await relaySignInStep(request, "/v1/auth/otp/verify", (body) =>
    withSignupAttribution(body, readAttributionCookie(request)),
  );
  if ("refusal" in step) {
    return step.refusal;
  }
  const { upstream, requestId } = step;

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
