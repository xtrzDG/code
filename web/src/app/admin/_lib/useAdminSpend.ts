"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";

/**
 * Today's provider spend (GET /v1/admin/spend). A minute old is fresh
 * enough: usage lands as turns and calls finish.
 */
export function useAdminSpend() {
  return useQuery(queryKeys.admin.spend(), () => api.GET("/v1/admin/spend"), { staleMs: 60_000 });
}
