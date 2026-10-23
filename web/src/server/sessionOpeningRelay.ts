/**
 * A sign-in step that ends with a session: the body (at most 256 KB) goes
 * to the API as it is, and a successful answer opens the session exactly
 * as /api/auth/verify does (httpOnly cookie, account language). A refusal
 * is passed on unchanged. Used by the passkey steps of the sign-in
 * (`/api/auth/mfa/passkey/verify` and `/api/auth/mfa/passkey/enroll/finish`).
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

export async function relayAndOpenSession(
  request: NextRequest,
  backendPath: string,
): Promise<Response> {
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
    upstream = await callBackend(backendPath, { method: "POST", headers, body });
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
