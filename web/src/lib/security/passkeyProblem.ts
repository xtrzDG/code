/**
 * The text of a passkey answer the API refused, or of a ceremony the
 * browser did not finish; null for other failures (a toast).
 */

import type { ApiError } from "@/api/errors";
import type { MessageKey } from "@/i18n/translate";

import { PasskeyCeremonyError } from "./passkeyCeremony";
import { hasReason, secondFactorProblem } from "./secondFactor";

export function passkeyApiProblem(error: ApiError): MessageKey | null {
  if (hasReason(error, "passkey_clone_suspected")) {
    return "passkeys.errors.suspended";
  }
  if (hasReason(error, "passkey_rejected")) {
    return "passkeys.errors.rejected";
  }
  if (hasReason(error, "passkeys_unavailable")) {
    return "passkeys.errors.unavailable";
  }
  return secondFactorProblem(error);
}

export function passkeyProblem(caught: unknown, error: ApiError): MessageKey | null {
  if (caught instanceof PasskeyCeremonyError) {
    return caught.messageKey;
  }
  return passkeyApiProblem(error);
}
