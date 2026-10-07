"use client";

import { useEffect } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";

import { DATA_TASKS_POLL_MS, type DataTask } from "./dataTasks";

/**
 * The post-deploy data tasks (GET /v1/admin/system/data-tasks), looked at
 * again every 30 seconds while the page is visible, and walking a failed
 * one again (POST …/{task_key}/retry, audited).
 */
export function useDataTasks() {
  const tasks = useQuery(queryKeys.admin.dataTasks(), () => api.GET("/v1/admin/system/data-tasks"), { staleMs: 0 });
  const { reload } = tasks;
  const retry = useMutation(
    (task: DataTask) =>
      api.POST("/v1/admin/system/data-tasks/{task_key}/retry", { params: { path: { task_key: task.key } } }),
    { invalidate: [queryKeys.admin.dataTasks()] },
  );

  useEffect(() => {
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        reload();
      }
    }, DATA_TASKS_POLL_MS);
    return () => window.clearInterval(timer);
  }, [reload]);

  /** True once the task is pending again. */
  const walkAgain = async (task: DataTask): Promise<boolean> => {
    const result = await retry.run(task);
    if (!result.ok && result.error.status === 409) {
      reload();
    }
    return result.ok;
  };

  return { tasks, walkAgain, isRetrying: retry.isPending };
}
