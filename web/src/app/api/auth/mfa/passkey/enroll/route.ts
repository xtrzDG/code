/**
 * POST /api/auth/mfa/passkey/enroll — a platform admin without a second
 * factor adds a passkey while signing in: {"mfa_challenge_id"} answers the
 * options for `navigator.credentials.create()`. No session exists yet.
 */

import type { NextRequest } from "next/server";

import { relayToBackend } from "@/server/relay";

export const dynamic = "force-dynamic";

export function POST(request: NextRequest): Promise<Response> {
  return relayToBackend(request, "/v1/auth/mfa/passkey/enroll", {
    useSession: false,
  });
}
