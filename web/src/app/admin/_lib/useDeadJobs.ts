"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { Schema } from "@/api/types";
import { useCursorPage } from "@/api/useCursorPage";
import { useMutation } from "@/api/useMutation";

import type { QueuedJob } from "./system";

const DEAD_JOBS_PAGE_SIZE = 20;

/**
 * The dead letters of the queue (GET /v1/admin/jobs?status=dead), and
 * running one again or dropping it (POST …/retry, …/discard; both audited).
 * A job that leaves the list is taken out at once and the page's counts are
 * loaded again. Retry failures are toasts; a discard shows its error in its
 * confirmation dialog.
 */
export function useDeadJobs() {
  const jobs = useCursorPage<QueuedJob, Schema<"QueuedJobPage">>(
    queryKeys.admin.deadJobs(),
    ({ cursor, limit }) =>
      api.GET("/v1/admin/jobs", { params: { query: { status: "dead", limit: String(limit), cursor: cursor ?? undefined } } }),
    { pageSize: DEAD_JOBS_PAGE_SIZE, staleMs: 0 },
  );
  const { updateItems, reload } = jobs;
  const retry = useMutation(
    (job: QueuedJob) => api.POST("/v1/admin/jobs/{job_id}/retry", { params: { path: { job_id: job.id } } }),
    { invalidate: [queryKeys.admin.system()] },
  );
  const discard = useMutation(
    (job: QueuedJob) => api.POST("/v1/admin/jobs/{job_id}/discard", { params: { path: { job_id: job.id } } }),
    { invalidate: [queryKeys.admin.system()], errorToast: false },
  );

  const settle = (job: QueuedJob, ok: boolean, status?: number) => {
    if (ok) {
      updateItems((items) => items.filter((item) => item.id !== job.id));
    } else if (status === 409) {
      // Someone else retried or discarded it meanwhile: show the list as it is.
      reload();
    }
    return ok;
  };

  /** True once the job is queued again. */
  const runAgain = async (job: QueuedJob): Promise<boolean> => {
    const result = await retry.run(job);
    return settle(job, result.ok, result.ok ? undefined : result.error.status);
  };

  /** True once the job is dropped. */
  const drop = async (job: QueuedJob): Promise<boolean> => {
    const result = await discard.run(job);
    return settle(job, result.ok, result.ok ? undefined : result.error.status);
  };

  return {
    jobs,
    runAgain,
    drop,
    isRetrying: retry.isPending,
    isDiscarding: discard.isPending,
    discardError: discard.error,
  };
}
