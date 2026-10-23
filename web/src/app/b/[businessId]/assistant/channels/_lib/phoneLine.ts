/**
 * A phone number the platform rents for the business (the phone line API,
 * `/v1/businesses/{id}/phone-line`): what the phone card shows, how the
 * search dialog groups countries, and the body that takes a number.
 */

import type { ReasonMessages } from "@/api/errors";
import type { CountryListItem, RequestBody, Schema } from "@/api/types";
import type { MessageKey } from "@/i18n/translate";

export type PhoneLineView = Schema<"PhoneLineView">;
export type RentedPhoneNumber = Schema<"RentedPhoneNumberView">;
export type PhoneNumberRequest = Schema<"PhoneNumberRequestView">;
export type PhoneNumberOffers = Schema<"PhoneNumberOfferList">;
export type PhoneNumberOffer = Schema<"PhoneNumberOfferView">;
export type PhoneNumberType = Schema<"PhoneNumberType">;
export type PhoneNumberAvailability = Schema<"PhoneNumberAvailability">;
export type RentPhoneNumberBody = RequestBody<"/v1/businesses/{business_id}/phone-line/number", "post">;
export type PhoneNumberRequestBody = RequestBody<"/v1/businesses/{business_id}/phone-line/request", "post">;

export const PHONE_NUMBER_TYPES: readonly PhoneNumberType[] = ["local", "mobile", "toll_free"];

/** Why the API refused to rent the chosen number (`reasons[].code`), in words. */
export const PHONE_NUMBER_REFUSALS: ReasonMessages = {
  number_taken: () => ({ key: "phoneNumbers.refusals.numberTaken" }),
  price_changed: () => ({ key: "phoneNumbers.refusals.priceChanged" }),
};

/**
 * A phone number inside a sentence: kept left to right (Unicode LRI ... PDI)
 * so "+1 512-555-0142?" does not come apart in a Hebrew sentence.
 */
export function numberInText(displayNumber: string): string {
  return `\u2066${displayNumber}\u2069`;
}

/**
 * One rented number's state on the card: answering, still being attached,
 * waiting for the assistant to be published with calls, or going back.
 */
export function rentedNumberState(number: RentedPhoneNumber): MessageKey {
  if (number.status !== "active") {
    return "phoneNumbers.panel.releasing";
  }
  if (!number.is_attached && !number.has_answering_agent) {
    return "phoneNumbers.panel.waitsForPublish";
  }
  return number.is_attached ? "phoneNumbers.panel.answering" : "phoneNumbers.panel.connecting";
}

/** Why the team arranges the number instead (only for a search that found no self-serve offer). */
export function teamArrangesReason(availability: PhoneNumberAvailability): MessageKey | null {
  if (availability === "requires_documents") {
    return "phoneNumbers.request.requires_documents";
  }
  return availability === "on_request" ? "phoneNumbers.request.on_request" : null;
}

export interface CountryGroups {
  /** Countries where the owner picks a number and has it at once. */
  now: CountryListItem[];
  /** Every other country: the team arranges the number from a request. */
  team: CountryListItem[];
}

/** The search dialog's countries: self-serve first, each group in the catalog's order (by name). */
export function groupCountries(countries: readonly CountryListItem[], selfServe: readonly string[]): CountryGroups {
  const now = new Set(selfServe.map((code) => code.toUpperCase()));
  return {
    now: countries.filter((country) => now.has(country.country_code)),
    team: countries.filter((country) => !now.has(country.country_code)),
  };
}

/** The country the dialog opens with: the business's own, or the first self-serve one when the catalog lacks it. */
export function initialCountry(line: PhoneLineView, countries: readonly CountryListItem[]): string {
  const own = line.default_country_code.toUpperCase();
  if (countries.length === 0 || countries.some((country) => country.country_code === own)) {
    return own;
  }
  return line.self_serve_countries?.[0] ?? countries[0]?.country_code ?? own;
}

/** The city to search near, or nothing for a blank field. */
export function cityQuery(city: string): string | undefined {
  const trimmed = city.trim();
  return trimmed === "" ? undefined : trimmed;
}

/**
 * Taking one offer: the number, its kind and the monthly price the owner
 * saw (the API refuses with `price_changed` when the price moved since).
 */
export function rentBody(offer: PhoneNumberOffer, offers: PhoneNumberOffers): RentPhoneNumberBody | null {
  if (!offers.monthly_price) {
    return null;
  }
  return {
    phone_number: offer.phone_number,
    number_type: offers.number_type,
    offer_token: offer.offer_token,
    monthly_price: offers.monthly_price.money,
    ...(offer.locality ? { locality: offer.locality } : {}),
  };
}
