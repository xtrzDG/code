"use client";

/**
 * The launch as state: the data processing agreement (accepted once, here
 * or in Settings), the free trial or the plan, and "Apply changes" with
 * its progress (useStagedApply). When the assistant is live, the tunnel
 * moves on to the finale.
 */

import { useEffect, useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { sectionQueries } from "@/api/sectionQueries";
import { usePlans } from "@/api/catalog";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { useI18n } from "@/i18n/client";

import type { StepContext } from "../flow/stepContext";
import { useStagedApply } from "./useStagedApply";

export function useLaunch(ctx: StepContext) {
  const { locale } = useI18n();
  const { business } = useBusiness();
  const { businessId } = ctx;
  const staged = useStagedApply(businessId, ctx.setup.apply);
  const { view, phase } = staged;
  const dpa = useQuery(queryKeys.settings.dpa(businessId), () =>
    api.GET("/v1/businesses/{business_id}/dpa", { params: { path: { business_id: businessId } } }),
  );
  const billingQuery = sectionQueries.billingOverview(businessId, locale);
  const billing = useQuery(billingQuery.key, billingQuery.fetch);
  const plans = usePlans(business.country_code);
  const trialDays = plans.data?.quotes.find((quote) => quote.plan_key === business.plan_key)?.trial_days ?? null;

  const [isAgreed, setAgreed] = useState(false);
  const [showAgreementError, setShowAgreementError] = useState(false);
  const acceptDpa = useMutation(() => api.POST("/v1/businesses/{business_id}/dpa", { params: { path: { business_id: businessId } } }), {
    stale: [queryKeys.assistant.all(businessId)],
  });

  // Live: everything the cabinet shows changed; the finale is next.
  const { refresh, goTo } = ctx;
  useEffect(() => {
    if (phase === "live") {
      refresh();
      goTo("done");
    }
  }, [phase, refresh, goTo]);

  const isAccepted = dpa.data?.is_current_version_accepted ?? false;

  const launch = async () => {
    if (!isAccepted) {
      if (!isAgreed) {
        setShowAgreementError(true);
        return;
      }
      const accepted = await acceptDpa.run();
      if (!accepted.ok) {
        return;
      }
      dpa.setData(accepted.data);
    }
    await staged.start();
  };

  return {
    view,
    phase,
    agreement: {
      isLoading: dpa.isLoading && !dpa.data,
      isAccepted,
      version: dpa.data?.current_document_version ?? "",
      hasText: Boolean(dpa.data?.document_url),
      isAgreed,
      setAgreed: (agreed: boolean) => {
        setAgreed(agreed);
        setShowAgreementError(false);
      },
      showError: showAgreementError && !isAgreed,
    },
    trial: {
      isAvailable: billing.data?.is_trial_available ?? null,
      hasPlan: Boolean(billing.data?.subscription),
      days: trialDays,
    },
    isStarting: acceptDpa.isPending || staged.isStarting,
    launch,
  };
}
