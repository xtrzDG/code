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

import type { NextRequest } from "next/server";

import { relayAndOpenSession } from "@/server/sessionOpeningRelay";

export const dynamic = "force-dynamic";

export function POST(request: NextRequest): Promise<Response> {
  return relayAndOpenSession(request, "/v1/auth/mfa/verify");
}
