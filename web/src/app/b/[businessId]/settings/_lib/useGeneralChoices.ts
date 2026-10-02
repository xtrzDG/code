"use client";

import { useMemo } from "react";

import { useCountryProfile } from "@/api/catalog";
import { api } from "@/api/client";
import { CATALOG_STALE_MS } from "@/api/catalog";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { useIsClient } from "@/components/workspace/useIsClient";
import { useI18n } from "@/i18n/client";
import { capitalizeFirst, languageName } from "@/lib/format";

import { languageChoices, type BusinessView, type GeneralForm } from "./general";

/** Every IANA zone the browser knows (for businesses outside the country's usual zones). */
function allTimeZones(): string[] {
  try {
    return Intl.supportedValuesOf("timeZone");
  } catch {
    return [];
  }
}

/**
 * What the General form offers: customer and owner languages (the
 * business's own, the country's, then any other the catalog knows) and the
 * time zones of the country, then every other zone the browser knows.
 */
export function useGeneralChoices(baseline: BusinessView, form: GeneralForm) {
  const { locale } = useI18n();
  const { business } = useBusiness();
  const isClient = useIsClient();
  const profile = useCountryProfile(business.country_code);
  const catalog = useQuery(
    queryKeys.catalog.languages(locale),
    () => api.GET("/v1/catalog/languages", { params: { query: { language: locale } } }),
    { staleMs: CATALOG_STALE_MS },
  );

  const catalogNames = useMemo(() => {
    const names = new Map<string, string>();
    for (const item of catalog.data?.languages ?? []) {
      names.set(item.profile.tag, capitalizeFirst(item.display_name, locale));
    }
    return names;
  }, [catalog.data, locale]);
  const labelOf = (tag: string) => catalogNames.get(tag) ?? languageName(tag, locale);

  const countryProfile = profile.data && profile.data.profile.country_code === business.country_code ? profile.data : undefined;
  const choices = languageChoices(
    baseline.languages,
    countryProfile?.default_customer_languages.map((option) => option.tag) ?? [],
    countryProfile?.on_request_customer_languages.map((option) => option.tag) ?? [],
    form.languages,
  );
  const addable = (catalog.data?.languages ?? [])
    .filter((item) => !choices.includes(item.profile.tag))
    .sort((left, right) => left.display_name.localeCompare(right.display_name, locale));
  const ownerLanguages = languageChoices(["ka", "ru", "en"], [baseline.owner_language], form.languages);

  const countryZones = countryProfile?.timezones ?? [];
  const browserZones = useMemo(() => (isClient ? allTimeZones() : []), [isClient]);
  const otherZones = browserZones.filter((zone) => !countryZones.some((option) => option.name === zone));

  return { labelOf, choices, addable, ownerLanguages, countryZones, otherZones };
}

export type GeneralChoices = ReturnType<typeof useGeneralChoices>;
