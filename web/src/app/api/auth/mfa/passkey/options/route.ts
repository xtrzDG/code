/**
 * POST /api/auth/mfa/passkey/options — the second step of a sign-in asks
 * for a passkey: {"mfa_challenge_id"} answers the options for
 * `navigator.credentials.get()` and the passkey challenge to answer with.
 * No session exists yet, so none is sent.
 */

import type { NextRequest } from "next/server";

import { relayToBackend } from "@/server/relay";

export const dynamic = "force-dynamic";

export function POST(request: NextRequest): Promise<Response> {
  return relayToBackend(request, "/v1/auth/mfa/passkey/options", {
    useSession: false,
  });
}
