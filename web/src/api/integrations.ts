"use client";

/**
 * Settings → Integrations: each integration's state and each resource's
 * calendars at a glance, shared by that page and the resources list (its
 * one-line summaries). Calendar changes invalidate it.
 */

import { api } from "./client";
import { queryKeys } from "./queryKeys";
import { useQuery } from "./useQuery";

export function useIntegrations(businessId: string, enabled = true) {
  return useQuery(
    queryKeys.integrations.list(businessId),
    () => api.GET("/v1/businesses/{business_id}/integrations", { params: { path: { business_id: businessId } } }),
    { enabled },
  );
}
