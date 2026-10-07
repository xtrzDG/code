"use client";

/**
 * The value endpoints of a business, shared by the dashboard and the
 * Reports page: the value of a period, saving the average check (both
 * views reload after it) and the signed-in owner's summaries.
 */

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { Schema } from "@/api/types";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";

import { DIGEST_REFUSAL_MESSAGES } from "./digestRefusals";

/** The value of local dates `from` to `to` (the dashboard's period), against as many days before. */
export function useValueOfDates(businessId: string, from: string, to: string, enabled = true) {
  return useQuery(
    queryKeys.dashboard.value(businessId, from, to),
    () =>
      api.GET("/v1/businesses/{business_id}/value", {
        params: { path: { business_id: businessId }, query: { from, to } },
      }),
    { keepPreviousData: true, enabled },
  );
}

/** The value of a named period of the API ("this_month", "last_month"). */
export function useValueOfPeriod(businessId: string, period: "this_month" | "last_month" | "last_week") {
  return useQuery(queryKeys.dashboard.valuePeriod(businessId, period), () =>
    api.GET("/v1/businesses/{business_id}/value", {
      params: { path: { business_id: businessId }, query: { period } },
    }),
  );
}

/** Sets the owner's average check (minor units), or clears it with null (the typical one applies). */
export function useSaveAverageCheck(businessId: string) {
  return useMutation(
    (averageCheckMinor: number | null) =>
      api.PUT("/v1/businesses/{business_id}/value/settings", {
        params: { path: { business_id: businessId } },
        body: { average_check_minor: averageCheckMinor },
      }),
    { invalidate: [queryKeys.dashboard.all(businessId), queryKeys.reports.all(businessId)] },
  );
}

/** What the PUT of the owner's summaries takes: the three switches, and channels when they change. */
export interface DigestPreferencesBody {
  is_daily_digest_on: boolean;
  is_weekly_digest_on: boolean;
  is_monthly_report_on: boolean;
  channels?: Schema<"DigestChannel">[];
  telegram_chat?: string;
  whatsapp_number?: string;
}

/** The signed-in owner's daily and weekly digests and monthly report, where they go, and saving them. */
export function useDigestPreferences(businessId: string) {
  const path = { business_id: businessId };
  const preferences = useQuery(queryKeys.reports.digests(businessId), () =>
    api.GET("/v1/businesses/{business_id}/digest-preferences", { params: { path } }),
  );
  const save = useMutation(
    (body: DigestPreferencesBody) => api.PUT("/v1/businesses/{business_id}/digest-preferences", { params: { path }, body }),
    { reasonMessages: DIGEST_REFUSAL_MESSAGES },
  );
  return { preferences, save };
}

/** Where customers came from in a named period: conversations, bookings and value per source (owners). */
export function useCustomerSources(businessId: string, period: "7d" | "30d" | "90d") {
  return useQuery(
    queryKeys.reports.sources(businessId, period),
    () =>
      api.GET("/v1/businesses/{business_id}/value/sources", {
        params: { path: { business_id: businessId }, query: { period } },
      }),
    { keepPreviousData: true },
  );
}

/** What customers asked about in the last 30 days, grouped every night, labelled in `language` (the cabinet's). */
export function useConversationTopics(businessId: string, language: string) {
  return useQuery(queryKeys.dashboard.topics(businessId, language), () =>
    api.GET("/v1/businesses/{business_id}/value/topics", {
      params: { path: { business_id: businessId }, query: { language } },
    }),
  );
}
