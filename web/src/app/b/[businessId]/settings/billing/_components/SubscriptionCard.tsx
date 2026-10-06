"use client";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { Badge, Button, Card, EmptyState, buttonClasses } from "@/components/ui";
import { Facts } from "@/components/workspace/Facts";
import { IconCard } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";

import {
  SUBSCRIPTION_STATUS_TONES,
  noSubscriptionText,
  quotedMoneyText,
  type BillingOverview,
  type SubscriptionStatus,
} from "../_lib/billing";

const SUBSCRIPTION_STATUS_LABELS: Record<SubscriptionStatus, MessageKey> = {
  incomplete: "billing.subscribe.statusIncomplete",
  trialing: "billing.status.trialing",
  active: "billing.status.active",
  past_due: "billing.status.past_due",
  cancelled: "billing.status.cancelled",
  paused: "billing.status.paused",
};

/** The current subscription: plan, price, dates, automatic payment and the owner's actions. */
export function SubscriptionCard({
  overview,
  canManage,
  canPay,
  canCancel,
  isPaying,
  onPay,
  onCancel,
}: {
  overview: BillingOverview;
  canManage: boolean;
  canPay: boolean;
  canCancel: boolean;
  isPaying: boolean;
  onPay: () => void;
  onCancel: () => void;
}) {
  const { t } = useI18n();
  const format = useBusinessFormat();
  const subscription = overview.subscription;
  const isPaused = subscription?.status === "paused";

  if (!subscription) {
    return (
      <Card title={t("billing.subscriptionTitle")} className="h-full">
        <EmptyState
          className="py-6"
          icon={<IconCard className="size-6" />}
          title={t("billing.noSubscriptionTitle")}
          description={t(noSubscriptionText(overview))}
          action={
            <a href="#billing-plans" className={buttonClasses({ variant: "secondary", size: "sm" })}>
              {t("billing.plans.title")}
            </a>
          }
        />
      </Card>
    );
  }

  return (
    <Card
      title={t("billing.subscriptionTitle")}
      className="h-full"
      actions={<Badge tone={SUBSCRIPTION_STATUS_TONES[subscription.status]}>{t(SUBSCRIPTION_STATUS_LABELS[subscription.status])}</Badge>}
      footer={
        canManage ? (
          <>
            {canCancel ? (
              <Button variant="danger-ghost" size="sm" onClick={onCancel}>
                {t("billing.cancel")}
              </Button>
            ) : null}
            {/* A paused subscription keeps its plan until it is resumed. */}
            {isPaused ? null : (
              <a href="#billing-plans" className={buttonClasses({ variant: "secondary", size: "sm" })}>
                {t("billing.changePlan")}
              </a>
            )}
            {canPay ? (
              <Button size="sm" onClick={onPay} isLoading={isPaying} loadingText={t("billing.paying")}>
                {t("billing.pay")}
              </Button>
            ) : null}
          </>
        ) : undefined
      }
    >
      <div className="space-y-5">
        <div>
          <p className="text-xl font-semibold text-ink">{subscription.plan_name}</p>
          <p className="mt-1 text-sm text-ink-muted">
            {t(subscription.billing_period === "annual" ? "billing.pricePer.annual" : "billing.pricePer.monthly", {
              price: quotedMoneyText(subscription.price, format.money),
            })}
          </p>
        </div>
        <Facts
          items={[
            subscription.status === "incomplete"
              ? { label: t("billing.facts.currentPeriod"), value: t("billing.subscribe.waitingForPayment") }
              : {
                  label: t("billing.facts.currentPeriod"),
                  value: t("billing.dateRange", { start: format.date(subscription.period_start), end: format.date(subscription.period_end) }),
                },
            subscription.status === "trialing" && subscription.trial_ends_at
              ? { label: t("billing.facts.trialEnds"), value: format.date(subscription.trial_ends_at) }
              : null,
            subscription.grace_until ? { label: t("billing.facts.graceUntil"), value: format.date(subscription.grace_until) } : null,
            subscription.pause_starts_at && subscription.pause_until
              ? {
                  label: t("billingLifecycle.facts.pause"),
                  value: t("billing.dateRange", {
                    start: format.date(subscription.pause_starts_at),
                    end: format.date(subscription.pause_until),
                  }),
                }
              : null,
            {
              label: t("billing.facts.billingPeriod"),
              value: t(subscription.billing_period === "annual" ? "billing.periodNames.annual" : "billing.periodNames.monthly"),
            },
            {
              label: t("billing.facts.autoDebit"),
              value: subscription.has_auto_debit ? t("billing.facts.autoDebitOn") : t("billing.facts.autoDebitOff"),
            },
            // A subscription waiting for its first payment serves nobody yet.
            subscription.status === "incomplete"
              ? null
              : {
                  label: t("billing.facts.serviceMode"),
                  value: (
                    // Requests only by the owner's choice during a pause: no alarm.
                    <Badge tone={overview.service_mode === "full" ? "success" : isPaused ? "info" : "danger"}>
                      {t(overview.service_mode === "full" ? "billing.serviceModes.full" : "billing.serviceModes.leads_only")}
                    </Badge>
                  ),
                },
          ]}
        />
      </div>
    </Card>
  );
}
