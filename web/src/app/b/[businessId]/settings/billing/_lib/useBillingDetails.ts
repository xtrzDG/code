"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";

import type { BillingProfileBody } from "./billingDetails";

/**
 * The billing details of the current business (owners): what invoices and
 * receipts name the buyer with, the VAT that follows, and saving them.
 */
export function useBillingDetails() {
  const { business } = useBusiness();
  const path = { business_id: business.id };
  const profile = useQuery(queryKeys.billing.profile(business.id), () =>
    api.GET("/v1/businesses/{business_id}/billing/profile", { params: { path } }),
  );
  const save = useMutation(
    (body: BillingProfileBody) => api.PUT("/v1/businesses/{business_id}/billing/profile", { params: { path }, body }),
    { errorToast: false },
  );
  return { profile, save };
}

export type BillingDetailsState = ReturnType<typeof useBillingDetails>;
