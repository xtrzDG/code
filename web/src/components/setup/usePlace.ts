"use client";

/**
 * "Where are you?" as values: the country (the one chosen, else the
 * owner's phone country, else a guess from the browser), what the country
 * brings (currency, time zones, customer languages) and the owner's
 * choices among them, kept per country so switching countries back and
 * forth loses nothing.
 */

import { useCountries, useCountryProfile } from "@/api/catalog";
import { guessCountryCode, isCountryAvailable, pickInitialTimezone } from "@/lib/countries";
import { systemTimeZone } from "@/lib/intl/calendarFields";
import { languageOptions } from "@/lib/tunnel/languageOptions";

export interface PlaceForm {
  countryCode: string | null;
  city: string;
  address: string;
  languagesByCountry: Record<string, string[]>;
  defaultByCountry: Record<string, string>;
  zoneByCountry: Record<string, string>;
}

export function usePlace(form: PlaceForm, userCountry: string | null | undefined) {
  const countries = useCountries();
  const list = countries.data?.countries ?? [];
  const available = list.filter(isCountryAvailable).map((country) => country.country_code);
  const phoneCountry = userCountry && available.includes(userCountry) ? userCountry : null;
  const countryCode =
    form.countryCode ??
    phoneCountry ??
    (available.length > 0 && typeof navigator !== "undefined"
      ? guessCountryCode(navigator.languages ?? [navigator.language], available)
      : null);

  const profile = useCountryProfile(countryCode);
  const defaults = profile.data && profile.data.profile.country_code === countryCode ? profile.data : undefined;
  const zones = defaults?.timezones ?? [];
  const languages =
    (countryCode ? form.languagesByCountry[countryCode] : undefined) ??
    defaults?.default_customer_languages.map((option) => option.tag) ??
    [];
  const chosenDefault = countryCode ? form.defaultByCountry[countryCode] : undefined;
  const defaultLanguage = chosenDefault && languages.includes(chosenDefault) ? chosenDefault : languages[0];
  const timezone =
    (countryCode ? form.zoneByCountry[countryCode] : undefined) ??
    (defaults
      ? pickInitialTimezone(
          zones.map((zone) => zone.name),
          defaults.default_timezone.name,
          systemTimeZone(),
        )
      : undefined);

  return {
    countries,
    countryList: list,
    countryCode,
    profile,
    defaults,
    options: languageOptions(defaults),
    zones,
    languages,
    defaultLanguage,
    timezone,
  };
}

export type PlaceValues = ReturnType<typeof usePlace>;

/** A form value changed for the current country only. */
export function forCountry<T>(values: Record<string, T>, countryCode: string | null, value: T): Record<string, T> {
  return countryCode ? { ...values, [countryCode]: value } : values;
}
