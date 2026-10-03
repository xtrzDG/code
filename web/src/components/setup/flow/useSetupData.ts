"use client";

/**
 * What the tunnel of an existing business reads: the guided setup (steps,
 * progress, links, the launch), the niche's starter answers (hours, booking
 * rules, examples, frequent questions) and the profile wizard (the niche's
 * questions with their answers, the saved profile). All in the interface
 * language, and loaded fresh when the tunnel opens.
 */

import { useCallback } from "react";

import { api } from "@/api/client";
import { invalidate } from "@/api/queryCache";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { useI18n } from "@/i18n/client";

export function useSetupData(businessId: string, enabled = true) {
  const { locale } = useI18n();
  const setup = useQuery(
    queryKeys.setup.progress(businessId, locale),
    () => api.GET("/v1/businesses/{business_id}/setup", { params: { path: { business_id: businessId }, query: { language: locale } } }),
    { requireFresh: true, enabled },
  );
  const starters = useQuery(
    queryKeys.setup.starters(businessId, locale),
    () =>
      api.GET("/v1/businesses/{business_id}/setup/starter-answers", {
        params: { path: { business_id: businessId }, query: { language: locale } },
      }),
    { enabled },
  );
  const wizard = useQuery(
    queryKeys.profile.wizard(businessId, locale),
    () =>
      api.GET("/v1/businesses/{business_id}/profile/wizard", {
        params: { path: { business_id: businessId }, query: { language: locale } },
      }),
    { requireFresh: true, enabled },
  );

  /** After a step saved something: the rail and the next screens read it again. */
  const refresh = useCallback(() => {
    invalidate(queryKeys.setup.all(businessId));
    invalidate(queryKeys.profile.all(businessId));
    invalidate(queryKeys.business.all(businessId));
    invalidate(queryKeys.assistant.all(businessId));
    invalidate(queryKeys.dashboard.all(businessId));
  }, [businessId]);

  return { setup, starters, wizard, refresh };
}

export type SetupData = ReturnType<typeof useSetupData>;
