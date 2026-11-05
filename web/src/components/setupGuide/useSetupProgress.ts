"use client";

/**
 * The guided setup of the current business (GET …/setup), shared by the
 * Overview's guide, the progress ring in the bar and the milestone
 * celebrations: one cached query, reloaded every `pollMs` while asked (the
 * phone check listens for the owner's message).
 */

import { useEffect } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { useI18n } from "@/i18n/client";

export function useSetupProgress(businessId: string, options: { enabled?: boolean; pollMs?: number } = {}) {
  const { locale } = useI18n();
  const { enabled = true, pollMs } = options;
  const query = useQuery(
    queryKeys.setup.progress(businessId, locale),
    () =>
      api.GET("/v1/businesses/{business_id}/setup", {
        params: { path: { business_id: businessId }, query: { language: locale } },
      }),
    { enabled },
  );
  const { reload } = query;
  useEffect(() => {
    if (!enabled || !pollMs) {
      return;
    }
    const timer = setInterval(reload, pollMs);
    return () => clearInterval(timer);
  }, [enabled, pollMs, reload]);
  return query;
}
