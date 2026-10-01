"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { api } from "@/api/client";
import { toApiError, type ApiError } from "@/api/errors";
import { useApiMutation, useApiQuery } from "@/api/hooks";
import { unwrap, type ApiResult } from "@/api/result";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { Alert, Button, Card, ErrorState, LoadingBlock, PageHeader, useToast } from "@/components/ui";
import { ConfirmDialog } from "@/components/workspace/ConfirmDialog";
import { OwnerOnlyState } from "@/components/workspace/OwnerOnly";
import { IconRefresh } from "@/components/workspace/icons";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

import { BillingNotices } from "./_components/BillingNotices";
import { InvoicesCard } from "./_components/InvoicesCard";
import { PlansSection, type PlanChoice } from "./_components/PlansSection";
import { SubscriptionCard } from "./_components/SubscriptionCard";
import { UsageCard } from "./_components/UsageCard";
import {
  billingNotices,
  canCancel as canCancelSubscription,
  canPay as canPaySubscription,
  checkoutReturnUrl,
  planPrice,
  quotedMoneyText,
  planSetupFee,
  type BillingOverview,
  type BillingPeriod,
  type CheckoutSession,
} from "./_lib/billing";

/** /billing: subscription, package usage, plans, invoices, payment (owner only). */
export function BillingScreen({ isCheckoutReturn }: { isCheckoutReturn: boolean }) {
  const { t, locale } = useI18n();
  const toast = useToast();
  const router = useRouter();
  const format = useBusinessFormat();
  const { business, isOwner } = useBusiness();
  const [chosenPeriod, setChosenPeriod] = useState<BillingPeriod | null>(null);
  const [choice, setChoice] = useState<PlanChoice | null>(null);
  const [isCancelling, setCancelling] = useState(false);
  const [dialogError, setDialogError] = useState<ApiError | null>(null);
  const [isPaying, setPaying] = useState(false);
  const [isSubscribing, setSubscribing] = useState(false);
  const [showReturnNotice, setShowReturnNotice] = useState(isCheckoutReturn);
  // "Now" for the trial countdown; the page is reloaded far more often than days pass.
  const [nowUs] = useState(() => Date.now() * 1000);

  const overview = useApiQuery(
    () =>
      api.GET("/v1/businesses/{business_id}/billing", {
        params: { path: { business_id: business.id }, query: { language: locale } },
      }),
    [business.id, locale],
  );
  const plans = useApiQuery(
    () => api.GET("/v1/catalog/plans", { params: { query: { country_code: business.country_code, language: locale } } }),
    [business.country_code, locale],
  );

  const pathParams = { path: { business_id: business.id }, query: { language: locale } };
  const startTrial = useApiMutation(
    (body: { plan_key: PlanChoice["quote"]["plan_key"]; billing_period: BillingPeriod }) =>
      api.POST("/v1/businesses/{business_id}/billing/trial", { params: pathParams, body }),
    { errorToast: false },
  );
  const changePlan = useApiMutation(
    (body: { plan_key: PlanChoice["quote"]["plan_key"]; billing_period: BillingPeriod }) =>
      api.POST("/v1/businesses/{business_id}/billing/plan", { params: pathParams, body }),
    { errorToast: false },
  );
  const cancel = useApiMutation(() => api.POST("/v1/businesses/{business_id}/billing/cancel", { params: pathParams }), {
    errorToast: false,
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
    const returnUrl = checkoutReturnUrl(window.location.origin, businessPath(business.id, "billing"));
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

  const periodName = (period: BillingPeriod) =>
    t(period === "annual" ? "billing.periodNames.annual" : "billing.periodNames.monthly").toLocaleLowerCase(locale);
  const pricePer = (choice: PlanChoice) =>
    t(choice.period === "annual" ? "billing.pricePer.annual" : "billing.pricePer.monthly", {
      price: quotedMoneyText(planPrice(choice.quote, choice.period), format.money),
    });

  const choiceTitle = (choice: PlanChoice): string => {
    switch (choice.action) {
      case "trial":
        return t("billing.dialogs.trialTitle", { plan: choice.quote.name });
      case "subscribe":
        return t("billing.subscribe.title", { plan: choice.quote.name, period: periodName(choice.period) });
      case "switch":
        return t("billing.dialogs.changeTitle", { plan: choice.quote.name, period: periodName(choice.period) });
    }
  };

  const choiceDescription = (choice: PlanChoice): string => {
    switch (choice.action) {
      case "trial":
        return t("billing.dialogs.trialDescription", { days: choice.quote.trial_days, price: pricePer(choice) });
      case "subscribe": {
        const price = quotedMoneyText(planPrice(choice.quote, choice.period), format.money);
        return choice.period === "annual"
          ? t("billing.subscribe.descriptionAnnual", { price })
          : t("billing.subscribe.description", { price, setup: quotedMoneyText(planSetupFee(choice.quote), format.money) });
      }
      case "switch":
        return t("billing.dialogs.changeDescription", { price: pricePer(choice) });
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

  const data = overview.data;
  const isOwnerOnly = overview.error?.code === "access_denied";
  const period = chosenPeriod ?? data?.subscription?.billing_period ?? "monthly";

  return (
    <>
      <PageHeader
        title={t("nav.billing")}
        description={t("pages.billing.description")}
        actions={
          data ? (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                overview.reload();
                plans.reload();
              }}
              leadingIcon={<IconRefresh className="size-4" aria-hidden />}
            >
              {t("workspace.refresh")}
            </Button>
          ) : undefined
        }
      />

      {isOwnerOnly ? (
        <Card>
          <OwnerOnlyState />
        </Card>
      ) : overview.error && !data ? (
        <Card>
          <ErrorState error={overview.error} onRetry={overview.reload} />
        </Card>
      ) : !data ? (
        <Card>
          <LoadingBlock label={t("common.loading")} />
        </Card>
      ) : (
        <div className="space-y-8">
          {showReturnNotice ? (
            <Alert tone="success" title={t("billing.notices.checkoutReturnTitle")}>
              <p>{t("billing.notices.checkoutReturn")}</p>
              <div className="mt-3">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => {
                    setShowReturnNotice(false);
                    overview.reload();
                    router.replace(businessPath(business.id, "billing"));
                  }}
                >
                  {t("workspace.refresh")}
                </Button>
              </div>
            </Alert>
          ) : null}

          <BillingNotices
            notices={billingNotices(data, nowUs)}
            overview={data}
            canPay={isOwner && canPaySubscription(data)}
            isPaying={isPaying}
            onPay={onPay}
          />

          <div className="grid gap-4 lg:grid-cols-2">
            <SubscriptionCard
              overview={data}
              canManage={isOwner}
              canPay={canPaySubscription(data)}
              canCancel={canCancelSubscription(data)}
              isPaying={isPaying}
              onPay={onPay}
              onCancel={openCancel}
            />
            <UsageCard usage={data.usage} />
          </div>

          <PlansSection
            quotes={plans.data?.quotes}
            exchangeRate={plans.data?.exchange_rate}
            error={plans.error}
            onRetry={plans.reload}
            overview={data}
            period={period}
            onPeriodChange={setChosenPeriod}
            canManage={isOwner}
            onChoose={openChoice}
          />

          <InvoicesCard invoices={data.invoices} />
        </div>
      )}

      <ConfirmDialog
        open={choice !== null}
        onClose={() => setChoice(null)}
        onConfirm={onConfirmChoice}
        tone="primary"
        isPending={startTrial.isPending || changePlan.isPending || isSubscribing}
        error={dialogError}
        errorOverrides={
          choice?.action === "subscribe"
            ? { conflict: "billing.errors.nothingToPay" }
            : { conflict: "billing.errors.trialUsed", not_found: "billing.errors.noSubscription" }
        }
        title={choice ? choiceTitle(choice) : ""}
        confirmLabel={
          choice?.action === "trial"
            ? t("billing.dialogs.trialConfirm")
            : choice?.action === "subscribe"
              ? t("billing.subscribe.confirm")
              : t("billing.dialogs.changeConfirm")
        }
      >
        {choice ? <p>{choiceDescription(choice)}</p> : null}
      </ConfirmDialog>

      <ConfirmDialog
        open={isCancelling}
        onClose={() => setCancelling(false)}
        onConfirm={onConfirmCancel}
        isPending={cancel.isPending}
        error={dialogError}
        title={t("billing.dialogs.cancelTitle")}
        confirmLabel={t("billing.dialogs.cancelConfirm")}
        cancelLabel={t("billing.dialogs.cancelKeep")}
      >
        {data?.subscription ? (
          <p>{t("billing.dialogs.cancelDescription", { date: format.date(data.subscription.period_end) })}</p>
        ) : null}
      </ConfirmDialog>
    </>
  );
}
