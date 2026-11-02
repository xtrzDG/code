/**
 * POST /api/auth/logout — end the session on the API and drop the cookie.
 * Always answers 204: a session the API no longer knows is gone anyway.
 *
 * The answer also asks the browser to forget everything the site kept on
 * this device (Clear-Site-Data: its cache, cookies and storage, the service
 * worker included), so the next person at a shared computer finds nothing
 * of the session; the sign-out button clears Web Storage itself too, for
 * browsers that ignore the header (components/shell/signOut.ts).
 */

import { NextResponse, type NextRequest } from "next/server";

import { callBackend } from "@/server/backend";
import { prepareBackendCall } from "@/server/relay";
import { clearSessionCookie } from "@/server/sessionCookie";

export const dynamic = "force-dynamic";

const CLEAR_SITE_DATA = '"cache", "cookies", "storage"';

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

  const response = new NextResponse(null, {
    status: 204,
    headers: { "clear-site-data": CLEAR_SITE_DATA, "cache-control": "no-store" },
  });
  clearSessionCookie(response);
  return response;
}
