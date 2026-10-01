/**
 * Backend-for-frontend proxy: /api/backend/v1/... -> BACKEND_URL/v1/...
 *
 * Adds `Authorization: Bearer <token>` from the httpOnly session cookie,
 * streams the answer back (JSON, or the audio of a call recording) with its
 * status, content type, caching rule and X-Request-ID, and drops the
 * session cookie when the API says the token is no longer valid.
 * Only /v1/* paths are forwarded.
 */

import type { NextRequest } from "next/server";

import { buildBackendPath, jsonError, REQUEST_ID_HEADER, sanitizeRequestId } from "@/server/backend";
import { relayToBackend } from "@/server/relay";

export const dynamic = "force-dynamic";

async function forward(
  request: NextRequest,
  context: RouteContext<"/api/backend/[...path]">,
): Promise<Response> {
  const { path } = await context.params;
  const backendPath = buildBackendPath(path);
  if (backendPath === null) {
    const requestId = sanitizeRequestId(request.headers.get(REQUEST_ID_HEADER));
    return jsonError(404, "not_found", "Unknown API path.", requestId);
  }
  return relayToBackend(request, backendPath, { useSession: true });
}

export { forward as DELETE, forward as GET, forward as PATCH, forward as POST, forward as PUT };
