"use client";

import { useEffect, useRef, useState } from "react";

import { api } from "@/api/client";
import { useApiQuery } from "@/api/hooks";
import { useBusiness } from "@/components/business/BusinessContext";
import { isRunInProgress } from "@/lib/assistant/autotests";

import { useAssistant } from "../../../_components/AssistantContext";

const POLL_INTERVAL_MS = 3000;

/**
 * One version and its autotest run. While the worker plays the autotests,
 * both are reloaded every few seconds (and the go-live checklist with them);
 * when the run ends, the version list is reloaded too.
 */
export function useVersionDetail(versionId: string) {
  const { business } = useBusiness();
  const { versions } = useAssistant();

  const version = useApiQuery(
    () =>
      api.GET("/v1/businesses/{business_id}/assistant-versions/{version_id}", {
        params: { path: { business_id: business.id, version_id: versionId } },
      }),
    [business.id, versionId],
  );
  // A version built without autotests has no run yet (the API answers 404).
  const hasRun = Boolean(version.data?.autotest_run_id) || version.data?.status === "testing";
  const run = useApiQuery(
    () =>
      api.GET("/v1/businesses/{business_id}/assistant-versions/{version_id}/autotest-run", {
        params: { path: { business_id: business.id, version_id: versionId } },
      }),
    [business.id, versionId],
    { enabled: hasRun },
  );

  const [checklistKey, setChecklistKey] = useState(0);

  const details = version.data;
  const runData = !hasRun || run.error?.code === "not_found" ? null : (run.data ?? null);
  const isRunning = isRunInProgress(details?.status, runData);

  // While the worker plays the autotests, refresh the version and its run.
  const { reload: reloadVersion } = version;
  const { reload: reloadRun } = run;
  const { reload: reloadVersions } = versions;
  const wasRunning = useRef(false);
  useEffect(() => {
    if (isRunning) {
      wasRunning.current = true;
      const timer = window.setInterval(() => {
        reloadVersion();
        reloadRun();
        setChecklistKey((key) => key + 1);
      }, POLL_INTERVAL_MS);
      return () => window.clearInterval(timer);
    }
    if (wasRunning.current) {
      wasRunning.current = false;
      reloadVersions();
    }
    return undefined;
  }, [isRunning, reloadVersion, reloadRun, reloadVersions]);

  return {
    version,
    run,
    hasRun,
    runData,
    isRunning,
    checklistKey,
    refreshChecklist: () => setChecklistKey((key) => key + 1),
  };
}
