import "server-only";

/**
 * A fresh session token after a step-up raised the session to two factors
 * (POST /api/auth/session/rotate): the API swaps the session's token
 * (POST /v1/auth/session/rotate: same person, level, device and end; the
 * old token answers what is already on its way for 30 seconds, as one
 * factor, then ends) and the new token goes into the httpOnly session
 * cookie exactly as at sign-in (sessionOpening.ts), never into the answer.
 * A token copied before the step-up so never gains its level. A refusal is
 * passed on; only a 401 (the session is gone) drops the cookie.
 */

import { NextResponse, type NextRequest } from "next/server";

import type { LoginSessionView } from "@/api/types";

import { callBackend, jsonError, pickResponseHeaders } from "./backend";
import { prepareBackendCall } from "./relay";
import { clearSessionCookie } from "./sessionCookie";
import { openSession } from "./sessionOpening";

const ROTATE_SESSION_PATH = "/v1/auth/session/rotate";

export async function rotateSession(request: NextRequest): Promise<Response> {
  const prepared = prepareBackendCall(request, { useSession: true, backendPath: ROTATE_SESSION_PATH });
  if ("refusal" in prepared) {
    return prepared.refusal;
  }
  const { requestId, headers, token } = prepared;
  if (!token) {
    return jsonError(401, "authentication_required", "Sign in again.", requestId);
  }

  let upstream: Response;
  try {
    upstream = await callBackend(ROTATE_SESSION_PATH, { method: "POST", headers, timeoutMs: 10_000 });
  } catch {
    return jsonError(502, "backend_unavailable", "The API is not reachable.", requestId);
  }

  if (!upstream.ok) {
    const refusal = new NextResponse(upstream.body, {
      status: upstream.status,
      headers: pickResponseHeaders(upstream.headers, requestId),
    });
    if (upstream.status === 401) {
      clearSessionCookie(refusal);
    }
    return refusal;
  }
  return openSession((await upstream.json()) as LoginSessionView, upstream.headers, requestId, request.headers);
}
