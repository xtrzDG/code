/**
 * Country and phone helpers for sign-in and business creation. Numbers are
 * parsed and validated by the API (any country, any format); these helpers
 * only present countries and catch obviously wrong input early.
 */

import type { ApiError } from "@/api/errors";
import type { CountryListItem } from "@/api/types";

import { REGION_NAMES } from "./displayNames.generated";

/** The first market: the default when nothing hints at the user's country. */
export const FALLBACK_COUNTRY_CODE = "GE";

/** Countries whose people usually set a region-less browser language. */
const COUNTRY_OF_LANGUAGE: Record<string, string> = {
  ka: "GE",
  hy: "AM",
  az: "AZ",
  tr: "TR",
  he: "IL",
  uk: "UA",
  kk: "KZ",
  ro: "RO",
  pl: "PL",
  de: "DE",
  fr: "FR",
  it: "IT",
  es: "ES",
  ja: "JP",
};

/** "GE" -> 🇬🇪 (regional indicator symbols). */
export function countryFlag(countryCode: string): string {
  const code = countryCode.trim().toUpperCase();
  if (!/^[A-Z]{2}$/.test(code)) {
    return "";
  }
  return String.fromCodePoint(...[...code].map((letter) => 0x1f1e6 + letter.charCodeAt(0) - 65));
}

/**
 * A country's name in the interface language: countryName("GE", "ka") ->
 * "საქართველო". The interface languages read the backend's CLDR table, so
 * the server and every browser say the same (Chrome has no Georgian region
 * names); other languages ask Intl.
 */
export function countryName(countryCode: string, locale: string): string {
  const code = countryCode.toUpperCase();
  const known = REGION_NAMES[baseLanguage(locale)]?.[code];
  if (known) {
    return known;
  }
  try {
    return new Intl.DisplayNames([locale], { type: "region" }).of(code) ?? countryCode;
  } catch {
    return countryCode;
  }
}

/** "ka-GE" -> "ka". */
function baseLanguage(locale: string): string {
  return locale.split(/[-_]/)[0]?.toLowerCase() ?? locale;
}

/** 995 -> "+995". */
export function formatCallingCode(callingCode: number): string {
  return `+${callingCode}`;
}

export function isCountryAvailable(country: Pick<CountryListItem, "onboarding_status">): boolean {
  return country.onboarding_status !== "restricted";
}

/** "🇬🇪 Georgia (+995)" for a country picker. */
export function countryOptionLabel(country: CountryListItem, unavailableNote?: string): string {
  const label = `${countryFlag(country.country_code)} ${country.display_name} (${formatCallingCode(country.calling_code)})`;
  return !isCountryAvailable(country) && unavailableNote ? `${label} — ${unavailableNote}` : label;
}

/** Countries matching a search by name (local or English), code or calling code. */
export function filterCountries(countries: readonly CountryListItem[], query: string): CountryListItem[] {
  const needle = query.trim().toLocaleLowerCase();
  if (needle === "") {
    return [...countries];
  }
  const digits = needle.replace(/^\+/, "");
  return countries.filter(
    (country) =>
      country.display_name.toLocaleLowerCase().includes(needle) ||
      country.english_name.toLocaleLowerCase().includes(needle) ||
      country.country_code.toLowerCase() === needle ||
      (/^\d+$/.test(digits) && String(country.calling_code).startsWith(digits)),
  );
}

/**
 * The user's likely country from the browser languages ("ka-GE", "en-US",
 * "ka"), limited to `available` codes; else `fallback` when available, else
 * the first available code.
 */
export function guessCountryCode(
  languages: readonly string[],
  available: readonly string[],
  fallback: string = FALLBACK_COUNTRY_CODE,
): string | null {
  const allowed = new Set(available.map((code) => code.toUpperCase()));
  for (const tag of languages) {
    const region = tag
      .split(/[-_]/)
      .slice(1)
      .find((part) => /^[A-Za-z]{2}$/.test(part))
      ?.toUpperCase();
    if (region && allowed.has(region)) {
      return region;
    }
  }
  for (const tag of languages) {
    const language = tag.split(/[-_]/)[0]?.toLowerCase() ?? "";
    const country = COUNTRY_OF_LANGUAGE[language];
    if (country && allowed.has(country)) {
      return country;
    }
  }
  if (allowed.has(fallback.toUpperCase())) {
    return fallback.toUpperCase();
  }
  return available[0]?.toUpperCase() ?? null;
}

/**
 * The time zone a new business starts with: the browser's own zone when it
 * is one of the country's zones (an owner in Vladivostok or Los Angeles),
 * else the country's default.
 */
export function pickInitialTimezone(
  countryZones: readonly string[],
  defaultZone: string,
  browserZone: string | null | undefined,
): string {
  return browserZone && countryZones.includes(browserZone) ? browserZone : defaultZone;
}

/** "+995 …" or "00995 …": the number carries its country code. */
export function hasInternationalPrefix(rawPhoneNumber: string): boolean {
  const trimmed = rawPhoneNumber.trim();
  return trimmed.startsWith("+") || trimmed.startsWith("00");
}

// Direction marks that chat apps and contact books wrap around copied numbers.
const BIDI_CONTROL_CHARACTERS = /[\u061C\u200E\u200F\u202A-\u202E\u2066-\u2069]/g;
const NON_ASCII_DECIMAL_DIGIT = /(?![0-9])\p{Nd}/gu;
const DECIMAL_DIGIT = /^\p{Nd}$/u;

/**
 * Full-width forms folded (NFKC), direction marks dropped and every Unicode
 * decimal digit (Arabic-Indic, Persian, Devanagari, full-width …) as ASCII.
 * Unicode encodes each digit set as a run of ten starting at zero.
 */
export function toAsciiDigits(value: string): string {
  return value
    .normalize("NFKC")
    .replace(BIDI_CONTROL_CHARACTERS, "")
    .replace(NON_ASCII_DECIMAL_DIGIT, (digit) => {
      const codePoint = digit.codePointAt(0) ?? 0;
      let runStart = codePoint;
      while (DECIMAL_DIGIT.test(String.fromCodePoint(runStart - 1))) {
        runStart -= 1;
      }
      return String((codePoint - runStart) % 10);
    });
}

/**
 * A quick plausibility check before asking the API: phone characters only
 * (digits of any script, hyphens of any kind) and 4–17 digits. The API does
 * the real parsing for the chosen country.
 */
export function looksLikePhoneNumber(rawPhoneNumber: string): boolean {
  const trimmed = toAsciiDigits(rawPhoneNumber).trim();
  if (!/^\+?[\d\s().\-/\u2010-\u2015\u2212]+$/.test(trimmed)) {
    return false;
  }
  const digits = trimmed.replace(/\D/g, "").length;
  return digits >= 4 && digits <= 17;
}

export function looksLikeEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(value.trim());
}

export type LoginMethod = "phone" | "email";

export interface OtpStartBody {
  phone_number?: string;
  email?: string;
  country_hint?: string;
  locale?: string;
}

/** The body of POST /api/auth/start for the chosen sign-in method. */
export function buildOtpStartBody(input: {
  method: LoginMethod;
  phoneNumber: string;
  email: string;
  countryCode: string | null;
  locale: string;
}): OtpStartBody {
  if (input.method === "email") {
    return { email: input.email.trim(), locale: input.locale };
  }
  return {
    phone_number: input.phoneNumber.trim(),
    ...(input.countryCode ? { country_hint: input.countryCode } : {}),
    locale: input.locale,
  };
}

export type OtpStartProblem =
  | "countryRestricted"
  | "resendTooSoon"
  | "cannotReceive"
  | "phoneInvalid"
  | "emailInvalid";

/**
 * Why the API refused to send a code, for a message next to the field.
 * Null means a general failure (shown as a toast).
 */
export function classifyOtpStartError(error: ApiError, method: LoginMethod): OtpStartProblem | null {
  switch (error.code) {
    case "access_denied":
      return "countryRestricted";
    case "rate_limited":
      return "resendTooSoon";
    case "validation_failed":
      if (method === "phone" && /cannot receive|sign in with e-mail|cannot be sent/i.test(error.detail ?? "")) {
        return "cannotReceive";
      }
      return method === "phone" ? "phoneInvalid" : "emailInvalid";
    default:
      return null;
  }
}

export type OtpVerifyProblem = "wrongCode" | "tooManyAttempts";

export function classifyOtpVerifyError(error: ApiError): OtpVerifyProblem | null {
  switch (error.code) {
    case "authentication_required":
    case "validation_failed":
    case "not_found":
      return "wrongCode";
    case "rate_limited":
      return "tooManyAttempts";
    default:
      return null;
  }
}
