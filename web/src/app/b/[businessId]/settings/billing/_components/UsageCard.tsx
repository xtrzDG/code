"use client";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { Card } from "@/components/ui";
import { UsageMeter } from "@/components/workspace/UsageMeter";
import { useI18n } from "@/i18n/client";

import { quotedMoneyText, type BillingOverview } from "../_lib/billing";

/** Voice minutes and dialogs of the package in the current billing window (warning from 80 %). */
export function UsageCard({ usage }: { usage: BillingOverview["usage"] }) {
  const { t } = useI18n();
  const format = useBusinessFormat();

  if (!usage) {
    return (
      <Card title={t("billing.usage.title")} className="h-full">
        <p className="text-sm text-ink-muted">{t("billing.usage.none")}</p>
      </Card>
    );
  }

  const hasEstimate = usage.overage_price_per_minute.is_estimated || usage.overage_cost.is_estimated;

  return (
    <Card
      title={t("billing.usage.title")}
      description={t("billing.dateRange", { start: format.date(usage.period_start), end: format.date(usage.period_end) })}
      className="h-full"
    >
      <div className="space-y-5">
        {usage.included_voice_minutes > 0 || usage.used_voice_minutes > 0 ? (
          <UsageMeter
            label={t("billing.usage.voice")}
            usedText={t("billing.usage.minutesOf", {
              used: format.number(usage.used_voice_minutes),
              included: format.number(usage.included_voice_minutes),
            })}
            percent={usage.voice_usage_percent}
          />
        ) : null}
        <UsageMeter
          label={t("billing.usage.dialogs")}
          usedText={t("billing.usage.dialogsOf", {
            used: format.number(usage.used_dialogs),
            included: format.number(usage.included_dialogs),
          })}
          percent={usage.dialog_usage_percent}
        />
        {usage.overage_voice_minutes > 0 ? (
          <div className="flex flex-wrap items-baseline justify-between gap-2 rounded-xl bg-warning-soft px-4 py-3 text-sm">
            <span className="font-medium text-warning">{t("billing.usage.overage")}</span>
            <span className="font-semibold text-ink">
              {t("billing.usage.overageValue", {
                minutes: format.number(usage.overage_voice_minutes),
                cost: quotedMoneyText(usage.overage_cost, format.money),
              })}
            </span>
          </div>
        ) : null}
        {usage.included_voice_minutes > 0 ? (
          <p className="text-xs text-ink-subtle">
            {t("billing.usage.overagePrice", { price: quotedMoneyText(usage.overage_price_per_minute, format.money) })}
            {hasEstimate ? ` ${t("billing.usage.estimatedNote")}` : ""}
          </p>
        ) : null}
      </div>
    </Card>
  );
}
