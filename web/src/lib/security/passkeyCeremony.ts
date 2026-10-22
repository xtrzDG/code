/**
 * The browser's half of a passkey ceremony: ask the authenticator (Touch
 * ID, Windows Hello, a phone, a security key) through
 * `navigator.credentials`, and turn its refusals into what the person is
 * told. The options come from the API; the answer goes back to it.
 */

import type {
  PasskeyCreationOptionsView,
  PasskeyRequestOptionsView,
} from "@/api/types";
import type { MessageKey } from "@/i18n/translate";

import {
  assertionJson,
  creationOptions,
  registrationJson,
  requestOptions,
  type AssertionCredentialJson,
  type RegistrationCredentialJson,
} from "./webauthnCodec";

/** Why a ceremony did not finish, as the person is told. */
export class PasskeyCeremonyError extends Error {
  constructor(readonly messageKey: MessageKey) {
    super(messageKey);
    this.name = "PasskeyCeremonyError";
  }
}

/** Whether this browser can use passkeys at all. */
export function canUsePasskeys(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.PublicKeyCredential === "function" &&
    typeof navigator.credentials?.create === "function"
  );
}

function refusal(error: unknown): PasskeyCeremonyError {
  const name = error instanceof Error ? error.name : "";
  if (name === "InvalidStateError") {
    return new PasskeyCeremonyError("passkeys.errors.alreadyAdded");
  }
  if (name === "NotAllowedError" || name === "AbortError") {
    return new PasskeyCeremonyError("passkeys.errors.cancelled");
  }
  if (name === "SecurityError") {
    return new PasskeyCeremonyError("passkeys.errors.wrongSite");
  }
  return new PasskeyCeremonyError("passkeys.errors.unsupported");
}

/** A new passkey from the authenticator, in the API's form. */
export async function createPasskey(
  options: PasskeyCreationOptionsView,
): Promise<RegistrationCredentialJson> {
  if (!canUsePasskeys()) {
    throw new PasskeyCeremonyError("passkeys.errors.unsupported");
  }
  let credential: Credential | null;
  try {
    credential = await navigator.credentials.create({
      publicKey: creationOptions(options),
    });
  } catch (error) {
    throw refusal(error);
  }
  if (!(credential instanceof PublicKeyCredential)) {
    throw new PasskeyCeremonyError("passkeys.errors.cancelled");
  }
  return registrationJson({
    rawId: credential.rawId,
    response: credential.response as AuthenticatorAttestationResponse,
  });
}

/** The authenticator's signed answer to a sign-in step or a step-up. */
export async function signWithPasskey(
  options: PasskeyRequestOptionsView,
): Promise<AssertionCredentialJson> {
  if (!canUsePasskeys()) {
    throw new PasskeyCeremonyError("passkeys.errors.unsupported");
  }
  let credential: Credential | null;
  try {
    credential = await navigator.credentials.get({
      publicKey: requestOptions(options),
    });
  } catch (error) {
    throw refusal(error);
  }
  if (!(credential instanceof PublicKeyCredential)) {
    throw new PasskeyCeremonyError("passkeys.errors.cancelled");
  }
  return assertionJson({
    rawId: credential.rawId,
    response: credential.response as AuthenticatorAssertionResponse,
  });
}
