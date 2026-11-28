/**
 * Settings → Calls, transfers to staff: the texts that depend on where the
 * business is (`business.country_code`). Telling staff about transferred
 * calls rests on Italian labour law (art. 4 of the Workers' Statute) only
 * for a business in Italy, and the help center's notice template is
 * written for Italy (the Workers' Statute, the Garante); everywhere else
 * the card asks the owner to tell the staff, without a law or a template
 * that does not apply. The staff number rule is the API's
 * (`is_transfer_destination_allowed`): a number of the business's own
 * country or of an EU member state, so "another EU country" reads right
 * only to a business in the EU.
 */

import type { MessageKey } from "@/i18n/translate";
import type { HelpArticleSlug } from "@/lib/help/helpTopics";

/**
 * The EU member states, as the API's transfer rule lists them
 * (`EU_COUNTRY_CODES` of app/utilities/channels/transfer_destinations.py;
 * tests/calls/test_transfer_texts_country_rules.py keeps the two lists equal).
 */
export const EU_COUNTRY_CODES: ReadonlySet<string> = new Set([
  "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GR", "HR",
  "HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI",
  "SK",
]);

interface NationalStaffNotice {
  /** The card's description naming the country's law. */
  description: MessageKey;
  /** The help article with the notice to give staff, written for that country. */
  template: HelpArticleSlug;
}

/** Countries whose labour law the card names, each with its notice template. */
const NATIONAL_STAFF_NOTICES: Readonly<Partial<Record<string, NationalStaffNotice>>> = {
  IT: { description: "callSettings.transfers.descriptionItaly", template: "staff-call-notice" },
};

export interface TransferTexts {
  description: MessageKey;
  numberRule: MessageKey;
  /** The notice template to link, or null where none is written for the business's country. */
  noticeTemplate: HelpArticleSlug | null;
}

export function transferTexts(countryCode: string): TransferTexts {
  const national = NATIONAL_STAFF_NOTICES[countryCode];
  return {
    description: national?.description ?? "callSettings.transfers.description",
    numberRule: EU_COUNTRY_CODES.has(countryCode) ? "callSettings.transfers.numberRuleEu" : "callSettings.transfers.numberRule",
    noticeTemplate: national?.template ?? null,
  };
}
