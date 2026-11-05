/**
 * Passkey calls of the sign-in's second step, through the cabinet's
 * /api/auth/mfa/passkey/* route handlers (which open the session cookie).
 * The ceremony itself runs in the browser (lib/security/passkeyCeremony.ts).
 */

import type {
  AssertionCredentialJson,
  RegistrationCredentialJson,
} from "@/lib/security/webauthnCodec";

import { postJson, type SignedInSession } from "./auth";
import type {
  PasskeyAssertionOptionsView,
  PasskeyRegistrationView,
} from "./types";

/** Options for `navigator.credentials.get()` of this sign-in step. */
export function startPasskeySignIn(
  mfaChallengeId: string,
): Promise<PasskeyAssertionOptionsView> {
  return postJson("/api/auth/mfa/passkey/options", {
    mfa_challenge_id: mfaChallengeId,
  });
}

/** The passkey's answer; on success the session cookie is set. */
export function finishPasskeySignIn(body: {
  mfa_challenge_id: string;
  passkey_challenge_id: string;
  credential: AssertionCredentialJson;
}): Promise<SignedInSession> {
  return postJson("/api/auth/mfa/passkey/verify", body);
}

/** A platform admin without a second factor starts adding a passkey. */
export function startPasskeyEnrollment(
  mfaChallengeId: string,
): Promise<PasskeyRegistrationView> {
  return postJson("/api/auth/mfa/passkey/enroll", {
    mfa_challenge_id: mfaChallengeId,
  });
}

/** The admin's new passkey; the session opens with its recovery codes. */
export function finishPasskeyEnrollment(body: {
  mfa_challenge_id: string;
  passkey_challenge_id: string;
  credential: RegistrationCredentialJson;
}): Promise<SignedInSession> {
  return postJson("/api/auth/mfa/passkey/enroll/finish", body);
}
