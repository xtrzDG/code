/**
 * Sign-in calls of the browser. They go to the cabinet's /api/auth/* route
 * handlers, which keep the bearer token in an httpOnly cookie.
 */

import type { OtpStartBody } from "@/lib/countries";

import { readApiError, toApiError } from "./errors";
import type { OtpChallengeView, UserView } from "./types";

export interface SignedInSession {
  user: UserView;
  is_new_user: boolean;
  expires_at: number;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      method: "POST",
      headers: { "content-type": "application/json", accept: "application/json" },
      body: JSON.stringify(body),
      credentials: "same-origin",
    });
  } catch (error) {
    throw toApiError(error);
  }
  if (!response.ok) {
    throw await readApiError(response);
  }
  return (await response.json()) as T;
}

/** Send a login code to a phone (any country) or an e-mail. */
export function startLogin(body: OtpStartBody): Promise<OtpChallengeView> {
  return postJson<OtpChallengeView>("/api/auth/start", body);
}

/** Check the code; on success the session cookie is set. */
export function verifyLogin(body: { challenge_id: string; code: string }): Promise<SignedInSession> {
  return postJson<SignedInSession>("/api/auth/verify", body);
}
