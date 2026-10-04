"use client";

import { useEffect } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { useI18n } from "@/i18n/client";
import { STATUS_POLL_MS, type PlatformStatus } from "@/lib/help/platformStatus";

/**
 * The platform's status (GET /v1/platform/status, public) in the interface
 * language, looked at again every minute while the page is visible.
 * `initial` is what the server already read (the status page).
 */
export function usePlatformStatus(initial?: PlatformStatus | null) {
  const { locale } = useI18n();
  const status = useQuery(
    queryKeys.platformStatus.status(locale),
    () => api.GET("/v1/platform/status", { params: { query: { language: locale } } }),
    { staleMs: STATUS_POLL_MS },
  );
  const { reload } = status;

  useEffect(() => {
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        reload();
      }
    }, STATUS_POLL_MS);
    return () => window.clearInterval(timer);
  }, [reload]);

  return { ...status, data: status.data ?? initial ?? undefined };
}
