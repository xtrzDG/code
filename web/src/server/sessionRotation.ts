import "server-only";

/**
 * A fresh session token after a proof raised the session to two factors
 * (POST /api/auth/session/rotate with {"rotation_ticket"}): the API takes
 * the one-time ticket that proof answered to this browser (a step-up, a
 * new authenticator or a first passkey) and swaps the session's token
 * (POST /v1/auth/session/rotate: same person, device and end, two factors;
 * the old token stays one factor, answers what is already on its way for
 * 30 seconds, then ends). The new token goes into the httpOnly session
 * cookie exactly as at sign-in (sessionOpening.ts), never into the answer.
 * Without the ticket nothing is asked (422), so a token copied before the
 * proof never gains its level. A refusal is passed on; only a 401 (the
 * session is gone) drops the cookie.
 */

import { NextResponse, type NextRequest } from "next/server";

import type { LoginSessionView } from "@/api/types";

import { callBackend, jsonError, pickResponseHeaders } from "./backend";
import { readLimitedText } from "./bodyLimits";
import { prepareBackendCall } from "./relay";
import { clearSessionCookie } from "./sessionCookie";
import { openSession } from "./sessionOpening";

const ROTATE_SESSION_PATH = "/v1/auth/session/rotate";
/** {"rotation_ticket": "<43 URL-safe characters>"} and nothing more. */
const ROTATION_BODY_LIMIT_BYTES = 256;
/** The API's SessionRotationTicket: 32 to 64 URL-safe characters. */
const ROTATION_TICKET = /^[A-Za-z0-9_-]{32,64}$/;
const NO_TICKET_MESSAGE = "The rotation ticket is missing or malformed.";

/** The ticket of the request's JSON body, or null when there is none. */
async function readRotationTicket(request: NextRequest): Promise<string | null> {
  let parsed: unknown;
  try {
    parsed = JSON.parse(await readLimitedText(request, ROTATION_BODY_LIMIT_BYTES));
  } catch {
    // Too large, or not JSON: no ticket.
    return null;
  }
  if (typeof parsed !== "object" || parsed === null) {
    return null;
  }
  const ticket = (parsed as { rotation_ticket?: unknown }).rotation_ticket;
  return typeof ticket === "string" && ROTATION_TICKET.test(ticket) ? ticket : null;
}

export async function rotateSession(request: NextRequest): Promise<Response> {
  const prepared = prepareBackendCall(request, { useSession: true, backendPath: ROTATE_SESSION_PATH });
  if ("refusal" in prepared) {
    return prepared.refusal;
  }
  const { requestId, headers, token } = prepared;
  if (!token) {
    return jsonError(401, "authentication_required", "Sign in again.", requestId);
  }
  const ticket = await readRotationTicket(request);
  if (!ticket) {
    return jsonError(422, "validation_failed", NO_TICKET_MESSAGE, requestId);
  }

  let upstream: Response;
  try {
    headers.set("content-type", "application/json");
    upstream = await callBackend(ROTATE_SESSION_PATH, {
      method: "POST",
      headers,
      body: JSON.stringify({ rotation_ticket: ticket }),
      timeoutMs: 10_000,
    });
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
