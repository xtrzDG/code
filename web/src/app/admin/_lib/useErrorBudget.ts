"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";

/**
 * The SLOs' error budgets (GET /v1/admin/system/error-budget). The hourly
 * rows change once an hour and the burn rate every five minutes: a minute
 * old is fresh enough.
 */
export function useErrorBudget() {
  return useQuery(queryKeys.admin.errorBudget(), () => api.GET("/v1/admin/system/error-budget"), {
    staleMs: 60_000,
  });
}
