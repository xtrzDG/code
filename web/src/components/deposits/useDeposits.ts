"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";

import type { DepositPolicyBody, DepositSettingsBody, PaymentLinkBody } from "./depositModel";
import { DEPOSIT_REFUSAL_MESSAGES } from "./depositRefusals";

/** The days the Reports card covers (the API takes 7 to 366). */
export const DEPOSIT_REPORT_DAYS = 30;

/** The business's deposits: on or off, the hold, the refund window, its payment pages and policies (owners). */
export function useDepositSettings(options: { enabled?: boolean } = {}) {
  const { business } = useBusiness();
  return useQuery(
    queryKeys.deposits.settings(business.id),
    () => api.GET("/v1/businesses/{business_id}/deposit-settings", { params: { path: { business_id: business.id } } }),
    { enabled: options.enabled },
  );
}

/**
 * Changing the deposit settings (owners; each change is audited): the
 * choices, a payment page added or removed, and the policy of a resource,
 * a service or the banquet requests. Every answer is the whole settings.
 */
export function useDepositSettingsActions() {
  const { business } = useBusiness();
  const path = { business_id: business.id };
  const settled = { reasonMessages: DEPOSIT_REFUSAL_MESSAGES, stale: [queryKeys.deposits.all(business.id)] };
  const save = useMutation(
    (body: DepositSettingsBody) => api.PUT("/v1/businesses/{business_id}/deposit-settings", { params: { path }, body }),
    { errorToast: false, reasonMessages: DEPOSIT_REFUSAL_MESSAGES },
  );
  const addPage = useMutation(
    (body: PaymentLinkBody) => api.POST("/v1/businesses/{business_id}/deposit-settings/payment-links", { params: { path }, body }),
    settled,
  );
  const removePage = useMutation(
    (linkId: string) =>
      api.DELETE("/v1/businesses/{business_id}/deposit-settings/payment-links/{link_id}", {
        params: { path: { ...path, link_id: linkId } },
      }),
    { ...settled, invalidate: [queryKeys.deposits.settings(business.id)] },
  );
  const setPolicy = useMutation(
    (body: DepositPolicyBody) => api.PUT("/v1/businesses/{business_id}/deposit-settings/policies", { params: { path }, body }),
    settled,
  );
  return { save, addPage, removePage, setPolicy };
}

/** One deposit asked: its reference and payment page, for a booking's details. */
export function useDepositRequest(requestId: string | null) {
  const { business } = useBusiness();
  return useQuery(
    queryKeys.deposits.request(business.id, requestId ?? ""),
    () =>
      api.GET("/v1/businesses/{business_id}/deposits/{deposit_id}", {
        params: { path: { business_id: business.id, deposit_id: requestId ?? "" } },
      }),
    { enabled: requestId !== null },
  );
}

/** "Paid": staff saw the money in their merchant account; the held booking is confirmed. */
export function useMarkDepositPaid() {
  const { business } = useBusiness();
  return useMutation(
    (requestId: string) =>
      api.POST("/v1/businesses/{business_id}/deposits/{deposit_id}/paid", {
        params: { path: { business_id: business.id, deposit_id: requestId } },
      }),
    {
      reasonMessages: DEPOSIT_REFUSAL_MESSAGES,
      // The lists show the new status at once (the caller replaces the booking).
      stale: [queryKeys.bookings.all(business.id), queryKeys.dashboard.all(business.id), queryKeys.deposits.all(business.id)],
    },
  );
}

/** Reports → Deposits: the last 30 days (owners). */
export function useDepositReport() {
  const { business } = useBusiness();
  return useQuery(queryKeys.deposits.report(business.id, DEPOSIT_REPORT_DAYS), () =>
    api.GET("/v1/businesses/{business_id}/deposit-report", {
      params: { path: { business_id: business.id }, query: { days: String(DEPOSIT_REPORT_DAYS) } },
    }),
  );
}
