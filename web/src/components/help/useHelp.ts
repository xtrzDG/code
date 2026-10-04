"use client";

/**
 * The help center's data through the API: articles and the search in the
 * interface language (the API answers in English where a language has no
 * article), the support contacts, and the signed-in person's progress (the
 * tips they have seen, the newest "What's new" entry they read).
 */

import { useCallback } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { Schema } from "@/api/types";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useI18n } from "@/i18n/client";

export type HelpArticle = Schema<"HelpArticleView">;
export type HelpCenter = Schema<"HelpCenterView">;
export type HelpProgress = Schema<"HelpProgressView">;
export type SupportContacts = Schema<"SupportContactsView">;

/** Articles change with a deployment only. */
const ARTICLE_STALE_MS = 10 * 60_000;

export function useHelpArticle(slug: string | null) {
  const { locale } = useI18n();
  const shown = slug ?? "";
  return useQuery(
    queryKeys.help.article(locale, shown),
    () => api.GET("/v1/help/{language}/{slug}", { params: { path: { language: locale, slug: shown } } }),
    { enabled: slug !== null, staleMs: ARTICLE_STALE_MS },
  );
}

export function useHelpCenter() {
  const { locale } = useI18n();
  return useQuery(
    queryKeys.help.center(locale),
    () => api.GET("/v1/help/{language}", { params: { path: { language: locale } } }),
    { staleMs: ARTICLE_STALE_MS },
  );
}

export function useHelpSearch(text: string) {
  const { locale } = useI18n();
  const query = text.trim();
  return useQuery(
    queryKeys.help.search(locale, query),
    () => api.GET("/v1/help/{language}/search", { params: { path: { language: locale }, query: { q: query } } }),
    { enabled: query.length > 0, staleMs: ARTICLE_STALE_MS, keepPreviousData: true },
  );
}

export function useSupportContacts() {
  return useQuery(queryKeys.help.support(), () => api.GET("/v1/support/contacts"), { staleMs: ARTICLE_STALE_MS });
}

/** The tips seen and "What's new" read; `enabled` only for a signed-in person. */
export function useHelpProgress(enabled = true) {
  const progress = useQuery(queryKeys.help.progress(), () => api.GET("/v1/me/help"), { enabled, staleMs: 5 * 60_000 });
  const { setData } = progress;
  const { run: runSeen } = useMutation(
    (key: string) => api.PUT("/v1/me/help/coach-marks/{key}", { params: { path: { key } } }),
    { errorToast: false },
  );
  const { run: runRead } = useMutation(
    (readKey: string) => api.PUT("/v1/me/help/changelog", { body: { read_key: readKey } }),
    { errorToast: false },
  );
  const reset = useMutation(() => api.DELETE("/v1/me/help/coach-marks"));

  /** Never shown again to this person, on any device. */
  const markSeen = useCallback(
    async (key: string) => {
      setData((current) =>
        current ? { ...current, seen_coach_marks: [...new Set([...current.seen_coach_marks, key])] } : current,
      );
      const result = await runSeen(key);
      if (result.ok) {
        setData(result.data);
      }
    },
    [setData, runSeen],
  );

  const markChangelogRead = useCallback(
    async (readKey: string) => {
      const result = await runRead(readKey);
      if (result.ok) {
        setData(result.data);
      }
    },
    [setData, runRead],
  );

  /** The tips show again; true once the API agreed. */
  const resetTips = async (): Promise<boolean> => {
    const result = await reset.run();
    if (result.ok) {
      setData((current) => (current ? { ...current, seen_coach_marks: [] } : current));
    }
    return result.ok;
  };

  return { progress, markSeen, markChangelogRead, resetTips, isResetting: reset.isPending };
}
