/**
 * POST /api/auth/logout — end the session on the API and drop the cookie.
 * Always answers 204: a session the API no longer knows is gone anyway.
 */

import { NextResponse, type NextRequest } from "next/server";

import { callBackend } from "@/server/backend";
import { prepareBackendCall } from "@/server/relay";
import { clearSessionCookie } from "@/server/sessionCookie";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest): Promise<Response> {
  const prepared = prepareBackendCall(request, { useSession: true });
  if ("refusal" in prepared) {
    return prepared.refusal;
  }

  if (prepared.token) {
    try {
      await callBackend("/v1/auth/logout", { method: "POST", headers: prepared.headers, timeoutMs: 10_000 });
    } catch {
      // The cookie is dropped below either way.
    }
  }

  const response = new NextResponse(null, { status: 204 });
  clearSessionCookie(response);
  return response;
}
