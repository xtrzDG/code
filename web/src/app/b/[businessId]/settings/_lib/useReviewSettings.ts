"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";

import { FEEDBACK_REQUEST_LIST_SIZE, type ReviewSettingsBody } from "./reviews";

/**
 * Settings → Reviews of the current business (owners): the settings with
 * the template texts, the last 30 days in numbers, the latest requests (a
 * view the API audits), and saving the settings.
 */
export function useReviewSettings() {
  const { business } = useBusiness();
  const path = { business_id: business.id };
  const settings = useQuery(queryKeys.reviews.settings(business.id), () =>
    api.GET("/v1/businesses/{business_id}/review-settings", { params: { path } }),
  );
  const stats = useQuery(queryKeys.reviews.stats(business.id), () =>
    api.GET("/v1/businesses/{business_id}/review-stats", { params: { path } }),
  );
  const requests = useQuery(queryKeys.reviews.requests(business.id), () =>
    api.GET("/v1/businesses/{business_id}/feedback-requests", {
      params: { path, query: { limit: String(FEEDBACK_REQUEST_LIST_SIZE) } },
    }),
  );
  const save = useMutation(
    (body: ReviewSettingsBody) => api.PUT("/v1/businesses/{business_id}/review-settings", { params: { path }, body }),
    { errorToast: false },
  );
  return { settings, stats, requests, save };
}

export type ReviewSettingsState = ReturnType<typeof useReviewSettings>;
