/**
 * Sign-in calls of the browser. They go to the cabinet's /api/auth/* route
 * handlers, which keep the bearer token in an httpOnly cookie.
 */

import type { OtpStartBody } from "@/lib/countries";

import { readApiError, toApiError } from "./errors";
import type {
  AuthLevel,
  MfaChallengeView,
  OtpChallengeView,
  TotpEnrollmentView,
  UserView,
} from "./types";

export interface SignedInSession {
  user: UserView;
  is_new_user: boolean;
  expires_at: number;
  auth_level: AuthLevel;
  /** Only right after an authenticator was set up at sign-in: shown once. */
  recovery_codes: string[];
}

/** The login code was right; the account asks for its second step. */
export interface SecondStepRequired {
  mfa_required: true;
  mfa_challenge: MfaChallengeView;
  is_new_user: boolean;
}

export type LoginCodeAnswer = SignedInSession | SecondStepRequired;

export function needsSecondStep(
  answer: LoginCodeAnswer,
): answer is SecondStepRequired {
  return "mfa_required" in answer && answer.mfa_required;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        accept: "application/json",
      },
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

/** Check the code: a session (cookie set), or the second step to take. */
export function verifyLogin(body: {
  challenge_id: string;
  code: string;
}): Promise<LoginCodeAnswer> {
  return postJson<LoginCodeAnswer>("/api/auth/verify", body);
}

/** The second step: an authenticator code or a recovery code; on success the session cookie is set. */
export function verifySecondStep(body: {
  mfa_challenge_id: string;
  code?: string;
  recovery_code?: string;
}): Promise<SignedInSession> {
  return postJson<SignedInSession>("/api/auth/mfa/verify", body);
}

/** A platform admin without an authenticator gets its secret and QR link. */
export function startSignInEnrollment(
  mfaChallengeId: string,
): Promise<TotpEnrollmentView> {
  return postJson<TotpEnrollmentView>("/api/auth/mfa/enroll", {
    mfa_challenge_id: mfaChallengeId,
  });
}
