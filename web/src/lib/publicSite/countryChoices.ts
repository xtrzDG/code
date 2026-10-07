/**
 * The countries of the public site's price picker, as the browser needs
 * them: a code, a label with the flag and whether it can be chosen. Made on
 * the server, so the page carries three short fields per country instead
 * of the whole catalog entry, and the browser no names or flags code.
 */

import type { CountryListItem } from "@/api/types";
import { countryFlag, isCountryAvailable } from "@/lib/countries";

export interface CountryChoice {
  code: string;
  /** "🇬🇪 Georgia", in the page's language (the catalog's display name). */
  label: string;
  /** A restricted country is listed but cannot be picked. */
  isAvailable: boolean;
}

export function countryChoices(countries: readonly CountryListItem[]): CountryChoice[] {
  return countries.map((country) => ({
    code: country.country_code,
    label: `${countryFlag(country.country_code)} ${country.display_name}`,
    isAvailable: isCountryAvailable(country),
  }));
}
