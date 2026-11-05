"use client";

/**
 * The changes customers do not get yet (GET …/assistant/pending-changes),
 * kept current: they are derived from the profile, the knowledge, the
 * bookable resources, the plan and the live version, so whenever one of
 * those sections is marked out of date (a save, a live event) they are
 * read again, once for a burst of saves. Saves that touch none of those
 * sections invalidate `queryKeys.assistant.pendingAll` themselves.
 */

import { useEffect } from "react";

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import { queryKeys } from "@/api/queryKeys";
import { useQuery, type Query } from "@/api/useQuery";
import { useI18n } from "@/i18n/client";
import { touchesPendingChanges, type PendingChangesView } from "@/lib/assistant/pendingChanges";

/** A burst of autosaves reloads the changes once, this long after the last one. */
const PENDING_RELOAD_DELAY_MS = 600;

export function usePendingChanges(businessId: string, enabled: boolean): Query<PendingChangesView> {
  const { locale } = useI18n();
  const key = queryKeys.assistant.pending(businessId, locale);
  const pending = useQuery(
    key,
    () =>
      api.GET("/v1/businesses/{business_id}/assistant/pending-changes", {
        params: { path: { business_id: businessId }, query: { language: locale } },
      }),
    { enabled, staleMs: 0 },
  );

  const { reload } = pending;
  useEffect(() => {
    if (!enabled) {
      return;
    }
    let timer: ReturnType<typeof setTimeout> | null = null;
    const stop = queryCache.onInvalidate((prefix) => {
      if (!touchesPendingChanges(prefix, businessId)) {
        return;
      }
      if (timer !== null) {
        clearTimeout(timer);
      }
      timer = setTimeout(reload, PENDING_RELOAD_DELAY_MS);
    });
    return () => {
      stop();
      if (timer !== null) {
        clearTimeout(timer);
      }
    };
  }, [enabled, businessId, reload]);

  return pending;
}
