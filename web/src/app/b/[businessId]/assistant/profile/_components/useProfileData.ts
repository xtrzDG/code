"use client";

/**
 * What the cards of Assistant → Business profile summarise: the profile
 * with its niche questions (read fresh, after the editors saved), the
 * business's knowledge (what is on offer, the ready answers) and the
 * "what to add" list, in the interface language.
 */

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { useI18n } from "@/i18n/client";

export function useProfileData(businessId: string) {
  const { locale } = useI18n();
  const wizard = useQuery(
    queryKeys.profile.wizard(businessId, locale),
    () =>
      api.GET("/v1/businesses/{business_id}/profile/wizard", {
        params: { path: { business_id: businessId }, query: { language: locale } },
      }),
    { requireFresh: true },
  );
  const knowledge = useQuery(
    queryKeys.knowledge.wizardItems(businessId, locale),
    () =>
      api.GET("/v1/businesses/{business_id}/knowledge", {
        params: { path: { business_id: businessId }, query: { language: locale, limit: "200" } },
      }),
    { requireFresh: true },
  );
  const gaps = useQuery(queryKeys.profile.gaps(businessId, locale), () =>
    api.GET("/v1/businesses/{business_id}/profile/gaps", {
      params: { path: { business_id: businessId }, query: { language: locale } },
    }),
  );
  return { wizard, knowledge, gaps };
}
