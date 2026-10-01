"use client";

import { api } from "@/api/client";
import { useApiQuery } from "@/api/hooks";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { Alert, Button, ButtonLink, Card, LoadingBlock } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

import { Meter } from "./DashboardWidgets";
import { usageLevel } from "./dashboardModel";

/**
 * Package minutes and dialogues of the current billing period (owners: the
 * billing overview is owner-only) with the 80% warning; staff see the voice
 * minutes of the dashboard period.
 */
export function PackageCard({ periodVoiceMinutes }: { periodVoiceMinutes: number }) {
  const { t, tp, locale } = useI18n();
  const { business, isOwner } = useBusiness();
  const format = useBusinessFormat();
  const businessId = business.id;

  const billing = useApiQuery(
    () =>
      api.GET("/v1/businesses/{business_id}/billing", {
        params: { path: { business_id: businessId }, query: { language: locale } },
      }),
    [businessId, locale],
    { enabled: isOwner },
  );

  if (!isOwner) {
    return (
      <Card title={t("dashboard.usage.title")}>
        <p className="text-sm text-ink-muted">{t("dashboard.usage.staffNote")}</p>
        <p className="mt-1 text-3xl font-semibold text-ink tabular-nums">
          {tp("dashboard.usage.minutes", periodVoiceMinutes)}
        </p>
      </Card>
    );
  }

  const usage = billing.data?.usage;
  return (
    <Card title={t("dashboard.usage.title")} description={usage ? t("dashboard.usage.periodUntil", { date: format.date(usage.period_end) }) : undefined}>
      {billing.error && !billing.data ? (
        <div className="space-y-3 text-sm">
          <p className="text-ink-muted">{t("dashboard.usage.loadFailed")}</p>
          <Button variant="secondary" size="sm" onClick={billing.reload}>
            {t("common.retry")}
          </Button>
        </div>
      ) : !billing.data ? (
        <LoadingBlock label={t("common.loading")} className="min-h-24" />
      ) : !usage ? (
        <div className="space-y-3">
          <p className="text-sm font-medium text-ink">{t("dashboard.usage.noPlanTitle")}</p>
          <p className="text-sm text-ink-muted">{t("dashboard.usage.noPlanDescription")}</p>
          <ButtonLink href={businessPath(businessId, "billing")} variant="secondary" size="sm">
            {t("dashboard.usage.toBilling")}
          </ButtonLink>
        </div>
      ) : (
        <div className="space-y-5">
          {usage.included_voice_minutes > 0 ? (
            <Meter
              label={t("dashboard.usage.voiceMinutes")}
              valueText={t("dashboard.usage.usedOf", {
                used: format.number(usage.used_voice_minutes),
                included: format.number(usage.included_voice_minutes),
              })}
              percent={usage.voice_usage_percent ?? 0}
              level={usageLevel(usage.voice_usage_percent)}
              used={usage.used_voice_minutes}
              max={usage.included_voice_minutes}
            />
          ) : (
            <div className="flex items-baseline justify-between gap-3 text-sm">
              <span className="font-medium text-ink">{t("dashboard.usage.voiceMinutes")}</span>
              <span className="text-ink-muted">{t("dashboard.usage.notIncluded")}</span>
            </div>
          )}
          {usage.included_dialogs > 0 ? (
            <Meter
              label={t("dashboard.usage.dialogs")}
              valueText={t("dashboard.usage.usedOf", {
                used: format.number(usage.used_dialogs),
                included: format.number(usage.included_dialogs),
              })}
              percent={usage.dialog_usage_percent ?? 0}
              level={usageLevel(usage.dialog_usage_percent)}
              used={usage.used_dialogs}
              max={usage.included_dialogs}
            />
          ) : null}
          {usage.overage_voice_minutes > 0 ? (
            <Alert tone="danger">
              {t("dashboard.usage.over", {
                minutes: format.number(usage.overage_voice_minutes),
                cost: usage.overage_cost.text,
              })}
            </Alert>
          ) : usageLevel(usage.voice_usage_percent) !== "ok" || usageLevel(usage.dialog_usage_percent) !== "ok" ? (
            <Alert tone="warning">
              {t("dashboard.usage.warning", { price: usage.overage_price_per_minute.text })}
            </Alert>
          ) : null}
        </div>
      )}
    </Card>
  );
}
