"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { api } from "@/api/client";
import { toApiError, type ApiError } from "@/api/errors";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import type { Query } from "@/api/useQuery";
import { unwrap, type ApiResult } from "@/api/result";
import { useBusiness } from "@/components/business/BusinessContext";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

import type { PlanChoice } from "../_components/PlansSection";
import { checkoutReturnUrl, type BillingOverview, type BillingPeriod, type CheckoutSession } from "./billing";

/**
 * What the owner does on the billing page: start a trial, subscribe (on
 * the payment page), switch plans, cancel, and pay what is due. Each
 * choice is confirmed in a dialog that shows a refusal.
 */
export function useBillingActions(overview: Query<BillingOverview>) {
  const { t, locale } = useI18n();
  const toast = useToast();
  const router = useRouter();
  const { business } = useBusiness();
  const [choice, setChoice] = useState<PlanChoice | null>(null);
  const [isCancelling, setCancelling] = useState(false);
  const [dialogError, setDialogError] = useState<ApiError | null>(null);
  const [isPaying, setPaying] = useState(false);
  const [isSubscribing, setSubscribing] = useState(false);

  const pathParams = { path: { business_id: business.id }, query: { language: locale } };
  // The package on the dashboard and the plan's channels follow a billing change.
  const settled = { stale: [queryKeys.dashboard.all(business.id), queryKeys.billing.all(business.id)] };
  const startTrial = useMutation(
    (body: { plan_key: PlanChoice["quote"]["plan_key"]; billing_period: BillingPeriod }) =>
      api.POST("/v1/businesses/{business_id}/billing/trial", { params: pathParams, body }),
    { errorToast: false, ...settled },
  );
  const changePlan = useMutation(
    (body: { plan_key: PlanChoice["quote"]["plan_key"]; billing_period: BillingPeriod }) =>
      api.POST("/v1/businesses/{business_id}/billing/plan", { params: pathParams, body }),
    { errorToast: false, ...settled },
  );
  const cancel = useMutation(() => api.POST("/v1/businesses/{business_id}/billing/cancel", { params: pathParams }), {
    errorToast: false,
    ...settled,
  });

  const applyOverview = (data: BillingOverview, message: string) => {
    overview.setData(data);
    // The business plan and service mode live in the layout's business too.
    router.refresh();
    toast.success(message);
  };

  const onConfirmChoice = async () => {
    if (!choice) {
      return;
    }
    const body = { plan_key: choice.quote.plan_key, billing_period: choice.period };
    if (choice.action === "subscribe") {
      setSubscribing(true);
      try {
        const session = await openPaymentPage((returnUrl) =>
          api.POST("/v1/businesses/{business_id}/billing/subscribe", {
            params: pathParams,
            body: returnUrl ? { ...body, return_url: returnUrl } : body,
          }),
        );
        window.location.assign(session.checkout_url);
      } catch (caught) {
        setSubscribing(false);
        setDialogError(toApiError(caught));
        // The plan may have been switched before the payment page failed.
        overview.reload();
        router.refresh();
      }
      return;
    }
    const result = choice.action === "trial" ? await startTrial.run(body) : await changePlan.run(body);
    if (result.ok) {
      setChoice(null);
      applyOverview(result.data, t(choice.action === "trial" ? "billing.dialogs.trialStarted" : "billing.dialogs.changed"));
    } else {
      setDialogError(result.error);
    }
  };

  const onConfirmCancel = async () => {
    const result = await cancel.run();
    if (result.ok) {
      setCancelling(false);
      applyOverview(result.data, t("billing.dialogs.cancelled"));
    } else {
      setDialogError(result.error);
    }
  };

  /**
   * Ask the API for the payment page with this billing page as the return
   * page. A cabinet origin the API does not list is refused as a return page
   * (422); the payment still works without one.
   */
  const openPaymentPage = async (
    request: (returnUrl: string | null) => Promise<ApiResult<CheckoutSession>>,
  ): Promise<CheckoutSession> => {
    const returnUrl = checkoutReturnUrl(window.location.origin, businessPath(business.id, "settings/billing"));
    try {
      return await unwrap(request(returnUrl));
    } catch (caught) {
      if (toApiError(caught).code !== "validation_failed") {
        throw caught;
      }
      return await unwrap(request(null));
    }
  };

  const onPay = async () => {
    setPaying(true);
    try {
      const session = await openPaymentPage((returnUrl) =>
        api.POST("/v1/businesses/{business_id}/billing/checkout", {
          params: pathParams,
          body: returnUrl ? { return_url: returnUrl } : {},
        }),
      );
      window.location.assign(session.checkout_url);
    } catch (caught) {
      setPaying(false);
      toast.error(caught, { conflict: "billing.errors.nothingToPay", not_found: "billing.errors.noSubscription" });
    }
  };

  const openChoice = (next: PlanChoice) => {
    setDialogError(null);
    setChoice(next);
  };
  const openCancel = () => {
    setDialogError(null);
    setCancelling(true);
  };

  return {
    choice,
    closeChoice: () => setChoice(null),
    openChoice,
    onConfirmChoice,
    isChoosing: startTrial.isPending || changePlan.isPending || isSubscribing,
    isCancelling,
    closeCancel: () => setCancelling(false),
    openCancel,
    onConfirmCancel,
    isCancelPending: cancel.isPending,
    dialogError,
    isPaying,
    onPay,
  };
}

export type BillingActions = ReturnType<typeof useBillingActions>;
