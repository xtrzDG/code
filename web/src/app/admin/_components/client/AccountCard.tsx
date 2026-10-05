"use client";

import type { Schema } from "@/api/types";
import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { Alert, Badge, Button, Card, useToast } from "@/components/ui";
import { Facts } from "@/components/workspace/Facts";
import { useI18n } from "@/i18n/client";
import { formatNumber } from "@/lib/format";

import { useClientFormat } from "../../_lib/useClientFormat";
import { PLAN_LABELS } from "../labels";

/** What the platform team granted the client: the trial's end, a discount, credit left, the setup fee. */
export function AccountCard({ client }: { client: Schema<"ClientHealthView"> }) {
  const { t, locale } = useI18n();
  const { date, money } = useClientFormat(client.timezone);
  const account = client.account;
  if (!account) {
    return (
      <Card title={t("adminActions.account.title")}>
        <p className="text-sm text-ink-muted">{t("adminActions.account.noSubscription")}</p>
      </Card>
    );
  }

  const discount = account.discount;
  const percent = discount ? formatNumber(discount.percent / 100, locale, { style: "percent" }) : "";
  // `ends_at` is the first moment after the last day: the day before it is the last one discounted.
  const lastDay = discount ? date(discount.ends_at - 1) : "";
  return (
    <Card title={t("adminActions.account.title")} description={t("adminActions.account.description")}>
      <Facts
        columns={2}
        items={[
          {
            label: t("adminActions.account.trialEnds"),
            value: account.trial_ends_at ? date(account.trial_ends_at) : t("adminActions.account.noTrial"),
          },
          {
            label: t("adminActions.account.discount"),
            value: discount ? (
              <span className="inline-flex flex-wrap items-center gap-2">
                <Badge tone={discount.is_active ? "accent" : "neutral"}>{percent}</Badge>
                <span className="font-normal text-ink-muted">
                  {t(discount.is_active ? "adminActions.account.discountActive" : "adminActions.account.discountEnded", {
                    percent,
                    date: lastDay,
                  })}
                </span>
              </span>
            ) : (
              t("adminActions.account.noDiscount")
            ),
          },
          {
            label: t("adminActions.account.credit"),
            value: account.credit_balance ? money(account.credit_balance.amount_minor, account.credit_balance.currency_code) : "—",
          },
          {
            label: t("adminActions.account.setupFee"),
            value: t(account.is_setup_fee_waived ? "adminActions.account.setupFeeWaived" : "adminActions.account.setupFeeCharged"),
          },
        ]}
      />
      {client.summary.has_auto_debit ? (
        <Alert tone="info" className="mt-4">
          {t("adminActions.autoDebitNote")}
        </Alert>
      ) : null}
    </Card>
  );
}

/**
 * The done-for-you setup the owner asked for, while it is open: when and on
 * which plan, and "Mark as done" for an admin who may write about clients.
 */
export function OnboardingRequestCard({
  businessId,
  client,
  canComplete,
}: {
  businessId: string;
  client: Schema<"ClientHealthView">;
  canComplete: boolean;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const { date } = useClientFormat(client.timezone);
  const complete = useMutation(
    () => api.POST("/v1/admin/clients/{business_id}/onboarding-request/done", { params: { path: { business_id: businessId } } }),
    { invalidate: [queryKeys.admin.client(businessId)] },
  );
  const request = client.summary.onboarding_request;
  if (!request || request.status !== "open") {
    return null;
  }

  const onComplete = async () => {
    const result = await complete.run();
    if (result.ok) {
      toast.success(t("adminActions.onboarding.marked"));
    }
  };
  return (
    <Card
      title={t("adminActions.onboarding.title")}
      actions={
        canComplete ? (
          <Button size="sm" variant="secondary" isLoading={complete.isPending} onClick={onComplete}>
            {t("adminActions.onboarding.markDone")}
          </Button>
        ) : null
      }
    >
      <p className="text-sm text-ink-muted">
        {t("adminActions.onboarding.description", { plan: t(PLAN_LABELS[request.plan_key]), date: date(request.requested_at) })}
      </p>
    </Card>
  );
}
