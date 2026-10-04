/**
 * POST /api/auth/mfa/enroll — a platform admin without an authenticator
 * app sets one up during the sign-in: {"mfa_challenge_id"} answers the
 * secret, its otpauth:// link (the QR code) and the account label. No
 * session exists yet, so none is sent.
 */

import type { NextRequest } from "next/server";

import { relayToBackend } from "@/server/relay";

export const dynamic = "force-dynamic";

export function POST(request: NextRequest): Promise<Response> {
  return relayToBackend(request, "/v1/auth/mfa/enroll", { useSession: false });
}
