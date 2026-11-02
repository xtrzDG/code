/**
 * POST /api/auth/session/rotate {"rotation_ticket"} — a fresh session
 * token after a proof raised the session to two factors (a step-up, a new
 * authenticator or a first passkey; src/server/sessionRotation.ts). The
 * new token replaces the httpOnly session cookie; the answer is that of a
 * sign-in: {"user", "is_new_user", "expires_at", "auth_level",
 * "recovery_codes"}. Called by the "confirm it is you" dialog and the
 * Account → Security cards (components/security/rotateSession.ts).
 */

import type { NextRequest } from "next/server";

import { rotateSession } from "@/server/sessionRotation";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest): Promise<Response> {
  return rotateSession(request);
}
