/**
 * Meta's refusals in the owner's words: the API's reason codes of a
 * Facebook sign-in (backend MetaConnectionRefusal) and the dialog's
 * fallbacks for an account another business uses or Meta not answering.
 */

import { toApiError, type ErrorMessageOverrides } from "@/api/errors";
import type { MessageKey } from "@/i18n/translate";

const REFUSAL_KEYS: Readonly<Record<string, MessageKey>> = {
  meta_link_expired: "metaConnect.refusals.meta_link_expired",
  meta_not_configured: "metaConnect.refusals.meta_not_configured",
  meta_permission_missing: "metaConnect.refusals.meta_permission_missing",
  whatsapp_account_missing: "metaConnect.refusals.whatsapp_account_missing",
  whatsapp_number_missing: "metaConnect.refusals.whatsapp_number_missing",
  whatsapp_pin_mismatch: "metaConnect.refusals.whatsapp_pin_mismatch",
  meta_page_not_found: "metaConnect.refusals.meta_page_not_found",
  instagram_account_missing: "metaConnect.refusals.instagram_account_missing",
};

/** The text of a Facebook sign-in refusal the API named, or null for any other failure. */
export function metaRefusalKey(error: unknown): MessageKey | null {
  if (!error) {
    return null;
  }
  const reason = toApiError(error).reasons.find((candidate) => Object.hasOwn(REFUSAL_KEYS, candidate.code));
  return reason ? (REFUSAL_KEYS[reason.code] ?? null) : null;
}

/** Other failures of the sign-in, as the manual connect form names them. */
export const META_ERROR_OVERRIDES: ErrorMessageOverrides = {
  conflict: "channels.errors.accountTaken",
  external_service_error: "channels.errors.provider",
};
