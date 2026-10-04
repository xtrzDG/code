/**
 * POST /api/auth/mfa/verify — the second step of a sign-in.
 *
 * Body: {"mfa_challenge_id", "code"} (an authenticator code) or
 * {"mfa_challenge_id", "recovery_code"} (at most 256 KB). On success the
 * session opens exactly as after /api/auth/verify (httpOnly cookie, account
 * language); right after an admin set up the authenticator, the answer
 * carries the new recovery codes, shown once. A wrong code is 422 with the
 * reason `wrong_code`; an expired step 401; too many wrong codes 429.
 */

import { NextResponse, type NextRequest } from "next/server";

import type { LoginSessionView } from "@/api/types";
import { callBackend, jsonError, pickResponseHeaders } from "@/server/backend";
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
    upstream = await callBackend("/v1/auth/mfa/verify", {
      method: "POST",
      headers,
      body,
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
  return openSession(
    (await upstream.json()) as LoginSessionView,
    upstream.headers,
    requestId,
  );
}
