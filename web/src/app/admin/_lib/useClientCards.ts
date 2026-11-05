"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";

/**
 * The reads of the admin client page's cards that load their own data,
 * shared by the card and its folded row on a phone (the row's summary
 * reads the same cached answer): the nightly judge's quality
 * (GET /v1/admin/clients/{business_id}/quality) and the team's sign-ins
 * (GET /v1/admin/clients/{business_id}/members).
 */
export function useClientQuality(businessId: string) {
  return useQuery(queryKeys.admin.clientQuality(businessId), () =>
    api.GET("/v1/admin/clients/{business_id}/quality", { params: { path: { business_id: businessId } } }),
  );
}

export function useClientMembers(businessId: string) {
  return useQuery(queryKeys.admin.clientMembers(businessId), () =>
    api.GET("/v1/admin/clients/{business_id}/members", { params: { path: { business_id: businessId } } }),
  );
}
