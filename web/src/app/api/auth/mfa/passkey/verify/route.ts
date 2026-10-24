/**
 * POST /api/auth/mfa/passkey/verify — the passkey's answer to the second
 * step: {"mfa_challenge_id", "passkey_challenge_id", "credential"}. On
 * success the session opens as after /api/auth/verify; a refused answer
 * is 422 (`passkey_rejected`, `passkey_clone_suspected`), an expired step
 * 401, too many tries 429.
 */

import type { NextRequest } from "next/server";

import { relayAndOpenSession } from "@/server/sessionOpeningRelay";

export const dynamic = "force-dynamic";

export function POST(request: NextRequest): Promise<Response> {
  return relayAndOpenSession(request, "/v1/auth/mfa/passkey/verify");
}
