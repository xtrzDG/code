"use client";

/**
 * State of the "new business" form: the typed fields, the country's
 * defaults (currency, zones, languages) with the owner's choices per
 * country, validation and POST /v1/businesses.
 */

import { useState, type FormEvent } from "react";
import { z } from "zod";

import { useCountries, useCountryProfile } from "@/api/catalog";
import { api } from "@/api/client";
import { useApiMutation } from "@/api/hooks";
import type { BusinessView, CurrentUserView, NicheKey } from "@/api/types";
import type { MessageKey } from "@/i18n/translate";
import { guessCountryCode, isCountryAvailable, pickInitialTimezone } from "@/lib/countries";
import { fieldErrors, messageKey } from "@/lib/validation";

import { languageOptions } from "./languageOptions";

export const MAX_NAME_LENGTH = 120;

const CreateBusinessSchema = z.object({
  name: z.string().trim().min(1, messageKey("businesses.errors.nameRequired")).max(MAX_NAME_LENGTH),
  niche_key: z.string().min(1, messageKey("businesses.errors.nicheRequired")),
  country_code: z.string().min(2, messageKey("businesses.errors.countryRequired")),
  city: z.string().trim().max(120),
  languages: z.array(z.string()).min(1, messageKey("businesses.errors.languagesRequired")),
});

type CreateBody = {
  name: string;
  niche_key: NicheKey;
  country_code: string;
  city?: string;
  timezone?: string;
  languages: string[];
  default_language?: string;
};

/** A value the owner chose for one country; switching countries keeps each country's choice. */
function usePerCountry<T>() {
  const [values, setValues] = useState<Record<string, T>>({});
  const set = (countryCode: string | null, value: T) => {
    if (countryCode) {
      setValues((current) => ({ ...current, [countryCode]: value }));
    }
  };
  return [values, set] as const;
}

export function useCreateBusiness(me: CurrentUserView, onCreated: (business: BusinessView) => void) {
  const countries = useCountries();
  const [name, setName] = useState("");
  const [nicheKey, setNicheKey] = useState("");
  const [chosenCountry, setChosenCountry] = useState<string | null>(null);
  const [city, setCity] = useState("");
  const [languagesByCountry, setLanguagesFor] = usePerCountry<string[]>();
  const [defaultByCountry, setDefaultFor] = usePerCountry<string>();
  const [zoneByCountry, setZoneFor] = usePerCountry<string>();
  const [errors, setErrors] = useState<Partial<Record<string, MessageKey>>>({});
  const [created, setCreated] = useState<BusinessView | null>(null);

  const countryList = countries.data?.countries ?? [];
  const availableCodes = countryList.filter(isCountryAvailable).map((country) => country.country_code);
  const userCountry = me.user.country_code && availableCodes.includes(me.user.country_code) ? me.user.country_code : null;
  const countryCode =
    chosenCountry ??
    userCountry ??
    (availableCodes.length > 0 && typeof navigator !== "undefined"
      ? guessCountryCode(navigator.languages ?? [navigator.language], availableCodes)
      : null);

  const profile = useCountryProfile(countryCode);
  const countryDefaults = profile.data && profile.data.profile.country_code === countryCode ? profile.data : undefined;
  const languages =
    (countryCode ? languagesByCountry[countryCode] : undefined) ??
    countryDefaults?.default_customer_languages.map((option) => option.tag) ??
    [];
  const chosenDefault = countryCode ? defaultByCountry[countryCode] : undefined;
  const defaultLanguage = chosenDefault && languages.includes(chosenDefault) ? chosenDefault : languages[0];
  const countryZones = countryDefaults?.timezones ?? [];
  const timezone =
    (countryCode ? zoneByCountry[countryCode] : undefined) ??
    (countryDefaults
      ? pickInitialTimezone(
          countryZones.map((zone) => zone.name),
          countryDefaults.default_timezone.name,
          typeof Intl !== "undefined" ? Intl.DateTimeFormat().resolvedOptions().timeZone : null,
        )
      : undefined);

  const create = useApiMutation((body: CreateBody) => api.POST("/v1/businesses", { body }), {
    errorMessages: { access_denied: "businesses.errors.countryRestricted" },
  });

  const toggleLanguage = (tag: string, checked: boolean) => {
    setLanguagesFor(countryCode, checked ? [...languages, tag] : languages.filter((item) => item !== tag));
    setErrors((current) => ({ ...current, languages: undefined }));
  };

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const parsed = CreateBusinessSchema.safeParse({ name, niche_key: nicheKey, country_code: countryCode ?? "", city, languages });
    setErrors(fieldErrors(parsed));
    if (!parsed.success) {
      return;
    }
    const result = await create.run({
      name: parsed.data.name,
      niche_key: parsed.data.niche_key as NicheKey,
      country_code: parsed.data.country_code,
      ...(parsed.data.city ? { city: parsed.data.city } : {}),
      ...(timezone ? { timezone } : {}),
      languages: parsed.data.languages,
      ...(defaultLanguage ? { default_language: defaultLanguage } : {}),
    });
    if (result.ok) {
      setCreated(result.data);
      onCreated(result.data);
    }
  }

  return {
    countries,
    countryList,
    countryCode,
    profile,
    countryDefaults,
    options: languageOptions(countryDefaults),
    countryZones,
    name,
    setName,
    nicheKey,
    setNicheKey,
    setCountry: setChosenCountry,
    city,
    setCity,
    languages,
    toggleLanguage,
    defaultLanguage,
    setDefaultLanguage: (tag: string) => setDefaultFor(countryCode, tag),
    timezone,
    setTimezone: (zone: string) => setZoneFor(countryCode, zone),
    errors,
    created,
    isSubmitting: create.isPending,
    submit,
  };
}

export type CreateBusinessState = ReturnType<typeof useCreateBusiness>;
