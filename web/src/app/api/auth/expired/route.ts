/**
 * GET /api/auth/expired?next=/path — Server Components send the browser here
 * when the API rejects the session (they cannot change cookies themselves).
 * Drops the session cookie and opens the sign-in page.
 */

import { NextResponse, type NextRequest } from "next/server";

import { loginPath } from "@/lib/navigation";
import { clearSessionCookie } from "@/server/relay";

export const dynamic = "force-dynamic";

export function GET(request: NextRequest): Response {
  const next = request.nextUrl.searchParams.get("next");
  const response = NextResponse.redirect(new URL(loginPath({ next, reason: "expired" }), request.url));
  clearSessionCookie(response);
  return response;
}
