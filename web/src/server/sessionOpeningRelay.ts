/**
 * A sign-in step that ends with a session: the body (at most 256 KB) goes
 * to the API as it is, and a successful answer opens the session exactly
 * as /api/auth/verify does (httpOnly cookie, account language). A refusal
 * is passed on unchanged. Used by the first step of the sign-in
 * (`/api/auth/verify`, which may answer with a second step instead), the
 * second step (`/api/auth/mfa/verify`) and its passkey steps
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

type SignInStep =
  | { refusal: Response }
  | { upstream: Response; requestId: string };

/**
 * The step's body, shaped by `shapeBody` (the first step adds where the
 * visitor came from), goes to `backendPath`. A refusal of the BFF or of
 * the API, or an API out of reach, comes back as `refusal`; a successful
 * answer as `upstream`, its body unread.
 */
export async function relaySignInStep(
  request: NextRequest,
  backendPath: string,
  shapeBody: (body: string) => string = (body) => body,
): Promise<SignInStep> {
  const prepared = prepareBackendCall(request, { useSession: false });
  if ("refusal" in prepared) {
    return prepared;
  }
  const { requestId, headers } = prepared;

  let body: string;
  try {
    body = await readLimitedText(request, DEFAULT_BODY_LIMIT_BYTES);
  } catch (error) {
    if (error instanceof BodyTooLargeError) {
      return {
        refusal: jsonError(413, "payload_too_large", error.message, requestId),
      };
    }
    throw error;
  }

  let upstream: Response;
  try {
    upstream = await callBackend(backendPath, {
      method: "POST",
      headers,
      body: shapeBody(body),
    });
  } catch {
    return {
      refusal: jsonError(
        502,
        "backend_unavailable",
        "The API is not reachable.",
        requestId,
      ),
    };
  }

  if (!upstream.ok) {
    return {
      refusal: new NextResponse(upstream.body, {
        status: upstream.status,
        headers: pickResponseHeaders(upstream.headers, requestId),
      }),
    };
  }
  return { upstream, requestId };
}

export async function relayAndOpenSession(
  request: NextRequest,
  backendPath: string,
): Promise<Response> {
  const step = await relaySignInStep(request, backendPath);
  if ("refusal" in step) {
    return step.refusal;
  }
  return openSession(
    (await step.upstream.json()) as LoginSessionView,
    step.upstream.headers,
    step.requestId,
  );
}
