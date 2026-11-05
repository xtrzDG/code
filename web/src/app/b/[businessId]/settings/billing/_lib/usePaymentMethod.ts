"use client";

import { useState } from "react";

import { api } from "@/api/client";
import { toApiError } from "@/api/errors";
import { queryKeys } from "@/api/queryKeys";
import { unwrap } from "@/api/result";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

import { cardReturnUrl, type CardSetupSession } from "./paymentMethod";

/**
 * The card on file of the current business (owners): the saved card, who
 * charges it, the trial's "Save card" prompt and the retries of a declined
 * charge; "Save card" / "Update card" opens the provider's page (Flitt's
 * verification of 0, Stripe's checkout or billing portal), which charges
 * nothing now and sends the owner back to this page.
 */
export function usePaymentMethod({ enabled }: { enabled: boolean }) {
  const { locale } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const [isOpening, setOpening] = useState(false);
  const path = { business_id: business.id };

  const method = useQuery(
    queryKeys.billing.paymentMethod(business.id),
    () => api.GET("/v1/businesses/{business_id}/billing/payment-method", { params: { path } }),
    { enabled },
  );

  const request = (returnUrl: string | null) =>
    unwrap<CardSetupSession>(
      api.POST("/v1/businesses/{business_id}/billing/payment-method", {
        params: { path, query: { language: locale } },
        body: returnUrl ? { return_url: returnUrl } : {},
      }),
    );

  /**
   * A cabinet origin the API does not list is refused as a return page
   * (422); the provider's page still works without one.
   */
  const openCardPage = async () => {
    setOpening(true);
    try {
      const returnUrl = cardReturnUrl(window.location.origin, businessPath(business.id, "settings/billing"));
      let session: CardSetupSession;
      try {
        session = await request(returnUrl);
      } catch (caught) {
        if (toApiError(caught).code !== "validation_failed") {
          throw caught;
        }
        session = await request(null);
      }
      window.location.assign(session.url);
    } catch (caught) {
      setOpening(false);
      toast.error(caught, { conflict: "billingCard.errors.cannotSave", not_found: "billing.errors.noSubscription" });
      method.reload();
    }
  };

  return { method, isOpening, openCardPage };
}

export type PaymentMethodState = ReturnType<typeof usePaymentMethod>;
