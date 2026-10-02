"use client";

/** Public catalog queries shared by several pages, in the interface language (cached for an hour). */

import { useI18n } from "@/i18n/client";

import { api } from "./client";
import { queryKeys } from "./queryKeys";
import { useQuery } from "./useQuery";

/** The catalog changes with a deploy, not while a page is open. */
export const CATALOG_STALE_MS = 60 * 60_000;

/** Every country with names in the interface language and calling codes. */
export function useCountries() {
  const { locale } = useI18n();
  return useQuery(
    queryKeys.catalog.countries(locale),
    () => api.GET("/v1/catalog/countries", { params: { query: { language: locale } } }),
    { staleMs: CATALOG_STALE_MS },
  );
}

/** One country's defaults (currency, time zone, languages), or nothing for null. */
export function useCountryProfile(countryCode: string | null) {
  const { locale } = useI18n();
  return useQuery(
    queryKeys.catalog.country(countryCode ?? "", locale),
    () =>
      api.GET("/v1/catalog/countries/{country_code}", {
        params: { path: { country_code: countryCode ?? "" }, query: { language: locale } },
      }),
    { enabled: countryCode !== null, staleMs: CATALOG_STALE_MS },
  );
}

/** The niches the platform supports, described in the interface language. */
export function useNiches() {
  const { locale } = useI18n();
  return useQuery(
    queryKeys.catalog.niches(locale),
    () => api.GET("/v1/catalog/niches", { params: { query: { language: locale } } }),
    { staleMs: CATALOG_STALE_MS },
  );
}

/** One niche (knowledge kinds, resource kind, booking unit, autotests), in the interface language. */
export function useNiche(nicheKey: string) {
  const { locale } = useI18n();
  return useQuery(
    queryKeys.catalog.niche(nicheKey, locale),
    () => api.GET("/v1/catalog/niches/{niche_key}", { params: { path: { niche_key: nicheKey }, query: { language: locale } } }),
    { staleMs: CATALOG_STALE_MS },
  );
}

/** The plans and prices of a country, in the interface language. */
export function usePlans(countryCode: string) {
  const { locale } = useI18n();
  return useQuery(
    queryKeys.catalog.plans(countryCode, locale),
    () => api.GET("/v1/catalog/plans", { params: { query: { country_code: countryCode, language: locale } } }),
    { staleMs: CATALOG_STALE_MS },
  );
}
