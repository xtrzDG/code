/**
 * POST /api/auth/start — send a one-time login code.
 *
 * Body: the API's StartOtpLoginCommand ({"phone_number", "country_hint"} or
 * {"email"}, plus "locale"). Answers the API's OtpChallengeView or error.
 */

import type { NextRequest } from "next/server";

import { relayToBackend } from "@/server/relay";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest): Promise<Response> {
  return relayToBackend(request, "/v1/auth/otp/start", { useSession: false });
}
