"use client";

/** Public catalog queries shared by several pages, in the interface language. */

import { useI18n } from "@/i18n/client";

import { api } from "./client";
import { useApiQuery } from "./hooks";

/** Every country with names in the interface language and calling codes. */
export function useCountries() {
  const { locale } = useI18n();
  return useApiQuery(
    () => api.GET("/v1/catalog/countries", { params: { query: { language: locale } } }),
    [locale],
  );
}

/** One country's defaults (currency, time zone, languages), or nothing for null. */
export function useCountryProfile(countryCode: string | null) {
  const { locale } = useI18n();
  return useApiQuery(
    () =>
      api.GET("/v1/catalog/countries/{country_code}", {
        params: { path: { country_code: countryCode ?? "" }, query: { language: locale } },
      }),
    [countryCode, locale],
    { enabled: countryCode !== null },
  );
}

/** The niches the platform supports, described in the interface language. */
export function useNiches() {
  const { locale } = useI18n();
  return useApiQuery(() => api.GET("/v1/catalog/niches", { params: { query: { language: locale } } }), [locale]);
}
