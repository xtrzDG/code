"use client";

import { useRouter } from "next/navigation";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery, type Query } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import type { BillingOverview } from "./billing";
import type { CancellationReason, RetentionOfferKind, SubscriptionLifecycle } from "./lifecycle";

export interface CancelBody {
  reason: CancellationReason;
  details: string | null;
  declined_offer: RetentionOfferKind | null;
}

export interface OfferBody {
  reason: CancellationReason;
  kind: RetentionOfferKind;
  pause_months?: number;
}

/**
 * The cancel dialog's offers and the pause card (GET …/billing/lifecycle),
 * and what the owner does with them: cancel saying why, take an offer
 * instead, pause for the season, resume. Each answers with the billing
 * page, which replaces the shown one; the offers load again after it.
 */
export function useSubscriptionLifecycle(overview: Query<BillingOverview>) {
  const { locale } = useI18n();
  const toast = useToast();
  const router = useRouter();
  const { business } = useBusiness();
  const pathParams = { path: { business_id: business.id }, query: { language: locale } };
  const lifecycle: Query<SubscriptionLifecycle> = useQuery(queryKeys.billing.lifecycle(business.id, locale), () =>
    api.GET("/v1/businesses/{business_id}/billing/lifecycle", { params: pathParams }),
  );
  // The dashboard's package and the layout's business follow a billing change.
  const settled = {
    errorToast: false,
    stale: [queryKeys.dashboard.all(business.id), queryKeys.billing.all(business.id)],
  };
  const cancel = useMutation(
    (body: CancelBody) => api.POST("/v1/businesses/{business_id}/billing/cancel", { params: pathParams, body }),
    settled,
  );
  const acceptOffer = useMutation(
    (body: OfferBody) => api.POST("/v1/businesses/{business_id}/billing/offers/accept", { params: pathParams, body }),
    settled,
  );
  const pause = useMutation(
    (months: number) => api.POST("/v1/businesses/{business_id}/billing/pause", { params: pathParams, body: { months } }),
    settled,
  );
  const resume = useMutation(() => api.POST("/v1/businesses/{business_id}/billing/resume", { params: pathParams }), settled);

  /** Shows the billing page the action answered with; false when it failed. */
  const applied = (data: BillingOverview, message: string): true => {
    overview.setData(data);
    router.refresh();
    toast.success(message);
    return true;
  };

  return {
    lifecycle,
    cancel,
    acceptOffer,
    pause,
    resume,
    applied,
    isPending: cancel.isPending || acceptOffer.isPending || pause.isPending || resume.isPending,
  };
}

export type SubscriptionLifecycleActions = ReturnType<typeof useSubscriptionLifecycle>;
