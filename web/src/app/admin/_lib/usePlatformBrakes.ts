"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";

/**
 * The global pause and the daily budget stop (GET /v1/admin/platform/pause),
 * and pausing or resuming every assistant with a reason (PUT, SUPER admins,
 * audited; a step-up the API asks for is handled by the API client). A
 * refusal stays in the dialog; the page's alerts load again after a change.
 */
export function usePlatformBrakes() {
  const brakes = useQuery(
    queryKeys.admin.platformBrakes(),
    () => api.GET("/v1/admin/platform/pause"),
    {
      staleMs: 30_000,
    },
  );
  const change = useMutation(
    (isPaused: boolean, reason: string) =>
      api.PUT("/v1/admin/platform/pause", {
        body: { is_paused: isPaused, reason },
      }),
    {
      errorToast: false,
      invalidate: [queryKeys.admin.platformBrakes(), queryKeys.admin.system()],
    },
  );

  /** True once the platform stands as asked. */
  const setPaused = async (
    isPaused: boolean,
    reason: string,
  ): Promise<boolean> => {
    const result = await change.run(isPaused, reason);
    return result.ok;
  };

  return {
    brakes,
    setPaused,
    isChanging: change.isPending,
    changeError: change.error,
  };
}

/** The latest daily payment reconciliation (SUPER and BILLING admins). */
export function usePaymentReconciliation() {
  return useQuery(
    queryKeys.admin.paymentReconciliation(),
    () => api.GET("/v1/admin/payments/reconciliation"),
    {
      staleMs: 300_000,
    },
  );
}
