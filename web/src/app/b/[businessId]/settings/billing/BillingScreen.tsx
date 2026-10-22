"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { sectionQueries } from "@/api/sectionQueries";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { useAutoReload } from "@/components/insights/useAutoReload";
import { LiveStatus } from "@/components/shell/LiveStatus";
import { Alert, Button, Card, ErrorState, LoadingRegion, PageHeader } from "@/components/ui";
import { OwnerOnlyState } from "@/components/workspace/OwnerOnly";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

import { BillingDetailsCard } from "./_components/BillingDetailsCard";
import { BillingDialogs } from "./_components/BillingDialogs";
import { BillingNotices } from "./_components/BillingNotices";
import { BillingSkeleton } from "./_components/BillingSkeleton";
import { CardReturnNotice, TrialCardPrompt } from "./_components/CardNotices";
import { InvoicesCard } from "./_components/InvoicesCard";
import { PauseCard } from "./_components/PauseCard";
import { PaymentMethodCard } from "./_components/PaymentMethodCard";
import { PlansSection } from "./_components/PlansSection";
import { SetupOptionsNote } from "./_components/SetupOptionsNote";
import { SubscriptionCard } from "./_components/SubscriptionCard";
import { UsageCard } from "./_components/UsageCard";
import {
  billingNotices,
  canCancel as canCancelSubscription,
  canPay as canPaySubscription,
  type BillingPeriod,
} from "./_lib/billing";
import { isCardConfirmed, withoutTrialNotice } from "./_lib/paymentMethod";
import { useBillingActions } from "./_lib/useBillingActions";
import { usePaymentMethod } from "./_lib/usePaymentMethod";
import { useSubscriptionLifecycle } from "./_lib/useSubscriptionLifecycle";

/** How often the page asks for the payment's confirmation after checkout. */
const CHECKOUT_RETURN_POLL_MS = 5_000;

function skipReload(): void {}

/**
 * /billing: subscription, package usage, the card for payments and its
 * retries, seasonal pause, plans, invoices with their PDFs, billing
 * details, payment, cancelling with a reason (owner only).
 */
export function BillingScreen({ isCheckoutReturn, isCardReturn }: { isCheckoutReturn: boolean; isCardReturn: boolean }) {
  const { t, locale } = useI18n();
  const router = useRouter();
  const { business, isOwner } = useBusiness();
  const [chosenPeriod, setChosenPeriod] = useState<BillingPeriod | null>(null);
  const [showReturnNotice, setShowReturnNotice] = useState(isCheckoutReturn);
  const [showCardNotice, setShowCardNotice] = useState(isCardReturn);
  // "Now" for the trial countdown; the page is reloaded far more often than days pass.
  const [nowUs] = useState(() => Date.now() * 1000);

  const overviewQuery = sectionQueries.billingOverview(business.id, locale);
  const overview = useQuery(overviewQuery.key, overviewQuery.fetch);
  // Priced as this business is billed: a further location of a brand pays the additional-location price.
  const plansQuery = sectionQueries.billingPlans(business.id, locale);
  const plans = useQuery(plansQuery.key, plansQuery.fetch);
  const pricing = plans.data
    ? { isAdditionalLocation: plans.data.is_additional_location ?? false, isSetupFeeCovered: plans.data.is_setup_fee_covered ?? false }
    : undefined;

  // Back from the payment page: the payment provider confirms in the
  // background, so the page asks again every few seconds until it shows.
  useAutoReload(showReturnNotice ? overview.reload : skipReload, {
    intervalMs: showReturnNotice ? CHECKOUT_RETURN_POLL_MS : null,
  });

  // The card on file (owners of a business with a subscription); back from
  // the provider's page, asked again until the new card shows.
  const card = usePaymentMethod({ enabled: isOwner && Boolean(overview.data?.subscription) });
  const isCardPending = showCardNotice && !isCardConfirmed(card.method.data, nowUs);
  useAutoReload(isCardPending ? card.method.reload : skipReload, {
    intervalMs: isCardPending ? CHECKOUT_RETURN_POLL_MS : null,
  });

  const actions = useBillingActions(overview);
  const lifecycle = useSubscriptionLifecycle(overview);
  const { isPaying, onPay, openCancel, openChoice } = actions;

  const data = overview.data;
  const isOwnerOnly = overview.error?.code === "access_denied";
  const period = chosenPeriod ?? data?.subscription?.billing_period ?? "monthly";

  return (
    <>
      <PageHeader
        title={t("navigation.pages.settingsBilling")}
        description={t("pages.billing.description")}
        status={data ? <LiveStatus updatedAt={overview.updatedAt} isFetching={overview.isFetching} /> : undefined}
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
        <LoadingRegion label={t("common.loading")}>
          <BillingSkeleton />
        </LoadingRegion>
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
                    router.replace(businessPath(business.id, "settings/billing"));
                  }}
                >
                  {t("common.close")}
                </Button>
              </div>
            </Alert>
          ) : null}

          {showCardNotice ? (
            <CardReturnNotice
              view={card.method.data}
              returnedAtUs={nowUs}
              onClose={() => {
                setShowCardNotice(false);
                router.replace(businessPath(business.id, "settings/billing"));
              }}
            />
          ) : null}

          <TrialCardPrompt
            view={card.method.data}
            nowUs={nowUs}
            canManage={isOwner}
            isOpening={card.isOpening}
            onSave={card.openCardPage}
          />

          <BillingNotices
            notices={withoutTrialNotice(billingNotices(data, nowUs), card.method.data)}
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

          {isOwner && data.subscription ? (
            <PaymentMethodCard state={card} canManage={isOwner} isTrial={data.subscription.status === "trialing"} />
          ) : null}

          <PauseCard overview={data} actions={lifecycle} canManage={isOwner} />

          <PlansSection
            quotes={plans.data?.quotes}
            pricing={pricing}
            exchangeRate={plans.data?.exchange_rate}
            error={plans.error}
            onRetry={plans.reload}
            overview={data}
            period={period}
            onPeriodChange={setChosenPeriod}
            canManage={isOwner}
            onChoose={openChoice}
          />

          <SetupOptionsNote subscription={data.subscription} />

          <InvoicesCard invoices={data.invoices} />

          <BillingDetailsCard />
        </div>
      )}

      <BillingDialogs actions={actions} lifecycle={lifecycle} data={data} />
    </>
  );
}
