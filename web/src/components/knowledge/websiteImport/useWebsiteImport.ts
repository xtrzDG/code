"use client";

import { useEffect, useState } from "react";

import { api } from "@/api/client";
import { isApiError } from "@/api/errors";
import { queryKeys } from "@/api/queryKeys";
import type { Schema } from "@/api/types";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { isImportRunning, type WebsiteImport } from "@/lib/knowledge/websiteImport";

/** While the worker reads the site and no live event arrives, look again this often. */
export const WEBSITE_IMPORT_POLL_MS = 3_000;

/**
 * The business's import from its website: the current one (if any), the
 * start of a new one, and the moment an import the person watched is done.
 * Progress comes from the `knowledge_import.progress` live events (the
 * query key is invalidated) and, as a fallback, from polling while it runs.
 */
export function useWebsiteImport(businessId: string) {
  const current = useQuery(
    queryKeys.knowledge.websiteImport(businessId),
    () =>
      api.GET("/v1/businesses/{business_id}/knowledge/import-website/current", {
        params: { path: { business_id: businessId } },
      }),
    { staleMs: 0 },
  );
  const start = useMutation(
    (url: string) =>
      api.POST("/v1/businesses/{business_id}/knowledge/import-website", {
        params: { path: { business_id: businessId } },
        body: { url },
      }),
    { errorToast: false },
  );
  const view: WebsiteImport | null = current.data?.current ?? null;
  const isRunning = isImportRunning(view);
  const { reload } = current;

  useEffect(() => {
    if (!isRunning) {
      return;
    }
    const timer = setInterval(reload, WEBSITE_IMPORT_POLL_MS);
    return () => clearInterval(timer);
  }, [isRunning, reload]);

  // An import this screen watched running has just finished (state
  // adjusted while rendering, React's pattern for "changed since last time").
  const [watchedId, setWatchedId] = useState<string | null>(null);
  const [finished, setFinished] = useState<WebsiteImport | null>(null);
  if (view && isRunning && watchedId !== view.id) {
    setWatchedId(view.id);
  } else if (view && !isRunning && watchedId === view.id) {
    setWatchedId(null);
    setFinished(view);
  }

  const begin = async (url: string): Promise<boolean> => {
    const result = await start.run(url);
    if (!result.ok) {
      // Another import runs already (another tab, a teammate): show it.
      if (isApiError(result.error) && result.error.status === 409) {
        reload();
      }
      return false;
    }
    setWatchedId(result.data.id);
    current.setData({ current: result.data } satisfies Schema<"CurrentWebsiteImport">);
    return true;
  };

  return {
    view,
    isLoading: current.isLoading,
    loadError: current.error,
    reload,
    isRunning,
    isStarting: start.isPending,
    startError: start.error,
    start: begin,
    /** The import that finished while this screen watched it (once). */
    finished,
    acknowledgeFinished: () => setFinished(null),
  };
}

export type WebsiteImportState = ReturnType<typeof useWebsiteImport>;
