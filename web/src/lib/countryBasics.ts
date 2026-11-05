/**
 * The country helpers a public page's browser code may carry: no name
 * tables (lib/countries.ts brings the generated region names, kilobytes on
 * the landing's first load). lib/countries.ts re-exports them.
 */

import type { CountryListItem } from "@/api/types";

/** "GE" -> 🇬🇪 (regional indicator symbols). */
export function countryFlag(countryCode: string): string {
  const code = countryCode.trim().toUpperCase();
  if (!/^[A-Z]{2}$/.test(code)) {
    return "";
  }
  return String.fromCodePoint(...[...code].map((letter) => 0x1f1e6 + letter.charCodeAt(0) - 65));
}

export function isCountryAvailable(country: Pick<CountryListItem, "onboarding_status">): boolean {
  return country.onboarding_status !== "restricted";
}
