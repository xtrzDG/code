/**
 * POST /api/auth/mfa/passkey/enroll/finish — the admin's new passkey:
 * {"mfa_challenge_id", "passkey_challenge_id", "credential", "name"?}. On
 * success the session opens and the answer carries the recovery codes,
 * shown once.
 */

import type { NextRequest } from "next/server";

import { relayAndOpenSession } from "@/server/sessionOpeningRelay";

export const dynamic = "force-dynamic";

export function POST(request: NextRequest): Promise<Response> {
  return relayAndOpenSession(request, "/v1/auth/mfa/passkey/enroll/finish");
}
