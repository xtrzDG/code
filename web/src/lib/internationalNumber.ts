/**
 * A phone number pasted or autofilled with its country: "+39 351 443 2225"
 * or "0039…" typed into a national-number field. The country with that
 * calling code takes the picker (the one already chosen first, so +1 stays
 * Canada for a Canadian) and the digits after it stay in the field, so a
 * number never carries its code twice.
 */

import type { CountryListItem } from "@/api/types";

import { isCountryAvailable } from "./countryBasics";

export interface InternationalNumber {
  countryCode: string;
  /** The digits after the calling code, as typed (spaces and dashes kept). */
  nationalNumber: string;
}

type Country = Pick<CountryListItem, "country_code" | "calling_code" | "onboarding_status">;

/** "+39 351…" -> "39 351…", "0039…" -> "39…"; null for a national number. */
function afterInternationalPrefix(value: string): string | null {
  const typed = value.trimStart();
  if (typed.startsWith("+")) {
    return typed.slice(1);
  }
  if (typed.startsWith("00")) {
    return typed.slice(2);
  }
  return null;
}

/** The country of the longest calling code the digits start with; the chosen one, then an available one, then any. */
function countryOfCallingCode(digits: string, countries: readonly Country[], chosen: string | null): Country | null {
  const matching = countries.filter((country) => digits.startsWith(String(country.calling_code)));
  const longest = Math.max(...matching.map((country) => String(country.calling_code).length), 0);
  const best = matching.filter((country) => String(country.calling_code).length === longest);
  return (
    best.find((country) => country.country_code === chosen) ??
    best.find(isCountryAvailable) ??
    best[0] ??
    null
  );
}

/**
 * The country and national part of a number typed with its calling code;
 * null for a national number (or a code no country has), which stays as
 * typed. The national part is empty while only the code is typed.
 */
export function splitInternationalNumber(
  value: string,
  countries: readonly Country[],
  chosenCountryCode: string | null,
): InternationalNumber | null {
  const rest = afterInternationalPrefix(value);
  if (rest === null) {
    return null;
  }
  const digits = rest.replace(/[\s().-]/g, "");
  if (!/^\d*$/.test(digits)) {
    return null;
  }
  const country = countryOfCallingCode(digits, countries, chosenCountryCode);
  if (country === null) {
    return null;
  }
  const code = String(country.calling_code);
  const national = rest.replace(/^[\s().-]*/, "").slice(code.length).replace(/^[\s().-]+/, "");
  return { countryCode: country.country_code, nationalNumber: national };
}
