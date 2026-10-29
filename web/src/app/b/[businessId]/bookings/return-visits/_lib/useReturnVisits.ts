"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useCursorPage } from "@/api/useCursorPage";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";

import type { CampaignMessage, CampaignMessagePage, CampaignSettingsBody } from "./returnVisitsModel";

const PAGE_SIZE = 20;

/**
 * Bookings → Return visits of the current business (owners): the settings
 * with the month so far and what customers read, the saved segments to
 * write to, the latest messages (a view the API audits), and saving.
 */
export function useReturnVisits(isOwner: boolean) {
  const { business } = useBusiness();
  const path = { business_id: business.id };
  const settings = useQuery(
    queryKeys.bookings.returnVisits(business.id),
    () => api.GET("/v1/businesses/{business_id}/campaign-settings", { params: { path } }),
    { enabled: isOwner },
  );
  const segments = useQuery(
    queryKeys.customers.segments(business.id),
    () => api.GET("/v1/businesses/{business_id}/customer-segments", { params: { path } }),
    { enabled: isOwner },
  );
  const messages = useCursorPage<CampaignMessage, CampaignMessagePage>(
    queryKeys.bookings.returnVisitMessages(business.id),
    ({ cursor, limit }) =>
      api.GET("/v1/businesses/{business_id}/campaign-messages", {
        params: { path, query: { limit: String(limit), cursor: cursor ?? undefined } },
      }),
    { pageSize: PAGE_SIZE, enabled: isOwner },
  );
  const save = useMutation(
    (body: CampaignSettingsBody) => api.PUT("/v1/businesses/{business_id}/campaign-settings", { params: { path }, body }),
    { errorToast: false },
  );
  return { settings, segments, messages, save };
}

export type ReturnVisitsState = ReturnType<typeof useReturnVisits>;
