"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { usePlans } from "@/api/catalog";
import { sectionQueries } from "@/api/sectionQueries";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { Alert, Button, Card, ErrorState, LoadingRegion, PageHeader } from "@/components/ui";
import { OwnerOnlyState } from "@/components/workspace/OwnerOnly";
import { IconRefresh } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

import { BillingDialogs } from "./_components/BillingDialogs";
import { BillingNotices } from "./_components/BillingNotices";
import { BillingSkeleton } from "./_components/BillingSkeleton";
import { InvoicesCard } from "./_components/InvoicesCard";
import { PlansSection } from "./_components/PlansSection";
import { SubscriptionCard } from "./_components/SubscriptionCard";
import { UsageCard } from "./_components/UsageCard";
import {
  billingNotices,
  canCancel as canCancelSubscription,
  canPay as canPaySubscription,
  type BillingPeriod,
} from "./_lib/billing";
import { useBillingActions } from "./_lib/useBillingActions";

/** /billing: subscription, package usage, plans, invoices, payment (owner only). */
export function BillingScreen({ isCheckoutReturn }: { isCheckoutReturn: boolean }) {
  const { t, locale } = useI18n();
  const router = useRouter();
  const { business, isOwner } = useBusiness();
  const [chosenPeriod, setChosenPeriod] = useState<BillingPeriod | null>(null);
  const [showReturnNotice, setShowReturnNotice] = useState(isCheckoutReturn);
  // "Now" for the trial countdown; the page is reloaded far more often than days pass.
  const [nowUs] = useState(() => Date.now() * 1000);

  const overviewQuery = sectionQueries.billingOverview(business.id, locale);
  const overview = useQuery(overviewQuery.key, overviewQuery.fetch);
  const plans = usePlans(business.country_code);

  const actions = useBillingActions(overview);
  const { isPaying, onPay, openCancel, openChoice } = actions;

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
                    overview.reload();
                    router.replace(businessPath(business.id, "settings/billing"));
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

      <BillingDialogs actions={actions} data={data} />
    </>
  );
}
