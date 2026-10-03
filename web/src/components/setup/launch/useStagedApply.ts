"use client";

/**
 * "Apply changes" as staged progress, shared by the tunnel's launch and
 * the cabinet's sheet: GET …/assistant/apply read again every 1.5 s while
 * it runs (the live event stream also reloads it as it moves on), and
 * POST …/assistant/apply to start it. The stages and the share done come
 * from lib/tunnel/launch.
 */

import { useCallback, useEffect } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { Schema } from "@/api/types";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useI18n } from "@/i18n/client";
import { LAUNCH_POLL_MS, launchPhase, shouldPoll, type LaunchPhase } from "@/lib/tunnel/launch";

export type ApplyChangesView = Schema<"ApplyChangesView">;

export interface StagedApply<View extends ApplyChangesView | null> {
  /** The latest progress (or `initial` until it loads). */
  view: View;
  phase: LaunchPhase;
  /** The start request is on its way. */
  isStarting: boolean;
  /** Starts "Apply changes"; true once it runs. */
  start: () => Promise<boolean>;
  reload: () => void;
}

export function useStagedApply<View extends ApplyChangesView | null>(
  businessId: string,
  initial: View,
  options: { enabled?: boolean } = {},
): StagedApply<View> {
  const { locale } = useI18n();
  const { enabled = true } = options;
  const apply = useQuery(
    queryKeys.setup.apply(businessId, locale),
    () =>
      api.GET("/v1/businesses/{business_id}/assistant/apply", {
        params: { path: { business_id: businessId }, query: { language: locale } },
      }),
    { enabled },
  );
  const view = (apply.data ?? initial) as View;
  const startMutation = useMutation(
    () => api.POST("/v1/businesses/{business_id}/assistant/apply", { params: { path: { business_id: businessId } } }),
    { stale: [queryKeys.assistant.all(businessId)] },
  );

  const phase = launchPhase(view);
  const isPolling = enabled && shouldPoll(view);
  const { reload, setData } = apply;

  // While it runs, ask how far it got.
  useEffect(() => {
    if (!isPolling) {
      return;
    }
    const timer = setInterval(reload, LAUNCH_POLL_MS);
    return () => clearInterval(timer);
  }, [isPolling, reload]);

  const { run } = startMutation;
  const start = useCallback(async () => {
    const started = await run();
    if (!started.ok) {
      return false;
    }
    setData(started.data);
    reload();
    return true;
  }, [run, setData, reload]);

  return { view, phase, isStarting: startMutation.isPending, start, reload };
}
