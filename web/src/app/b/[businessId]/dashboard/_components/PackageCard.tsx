"use client";

import { api } from "@/api/client";
import { useApiQuery } from "@/api/hooks";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import type { DashboardPackageUsage } from "@/components/insights/types";
import { Alert, ButtonLink, Card } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

import { Meter } from "./DashboardWidgets";
import { usageLevel } from "./dashboardModel";

/**
 * Package minutes and dialogues of the current billing window (from the
 * dashboard, so staff see them too) with the 80% warning. Prices are for
 * owners only: their warning names the price of an extra minute from the
 * owner-only billing overview.
 */
export function PackageCard({
  usage,
  periodVoiceMinutes,
}: {
  usage: DashboardPackageUsage | null;
  periodVoiceMinutes: number;
}) {
  const { t, tp, locale } = useI18n();
  const { business, isOwner } = useBusiness();
  const format = useBusinessFormat();
  const businessId = business.id;
  const voiceLevel = usage ? usageLevel(usage.voice_usage_percent) : "ok";
  const dialogLevel = usage ? usageLevel(usage.dialog_usage_percent) : "ok";
  const needsPrice = isOwner && usage !== null && (voiceLevel !== "ok" || dialogLevel !== "ok");

  const billing = useApiQuery(
    () =>
      api.GET("/v1/businesses/{business_id}/billing", {
        params: { path: { business_id: businessId }, query: { language: locale } },
      }),
    [businessId, locale],
    { enabled: needsPrice },
  );
  const prices = billing.data?.usage ?? null;

  if (!usage) {
    return (
      <Card title={t("dashboard.usage.title")}>
        <div className="space-y-3">
          <p className="text-sm font-medium text-ink">{t("dashboard.usage.noPlanTitle")}</p>
          <p className="text-sm text-ink-muted">
            {t(isOwner ? "dashboard.usage.noPlanDescription" : "dashboard.usage.noPlanStaff")}
          </p>
          {isOwner ? (
            <ButtonLink href={businessPath(businessId, "billing")} variant="secondary" size="sm">
              {t("dashboard.usage.toBilling")}
            </ButtonLink>
          ) : null}
        </div>
      </Card>
    );
  }

  return (
    <Card
      title={t("dashboard.usage.title")}
      description={t("dashboard.usage.periodUntil", { date: format.date(usage.period_end) })}
    >
      <div className="space-y-5">
        {usage.included_voice_minutes > 0 ? (
          <Meter
            label={t("dashboard.usage.voiceMinutes")}
            valueText={t("dashboard.usage.usedOf", {
              used: format.number(usage.used_voice_minutes),
              included: format.number(usage.included_voice_minutes),
            })}
            percent={usage.voice_usage_percent ?? 0}
            level={voiceLevel}
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
            level={dialogLevel}
            used={usage.used_dialogs}
            max={usage.included_dialogs}
          />
        ) : null}
        {usage.overage_voice_minutes > 0 ? (
          <Alert tone="danger">
            {prices
              ? t("dashboard.usage.over", {
                  minutes: format.number(usage.overage_voice_minutes),
                  cost: prices.overage_cost.text,
                })
              : t("dashboard.usage.overStaff", { minutes: format.number(usage.overage_voice_minutes) })}
          </Alert>
        ) : voiceLevel !== "ok" || dialogLevel !== "ok" ? (
          <Alert tone="warning">
            {prices
              ? t("dashboard.usage.warning", { price: prices.overage_price_per_minute.text })
              : t("dashboard.usage.warningStaff")}
          </Alert>
        ) : null}
        <p className="border-t border-line pt-3 text-xs text-ink-muted">
          {t("dashboard.usage.periodMinutes", { minutes: tp("dashboard.usage.minutes", periodVoiceMinutes) })}
        </p>
      </div>
    </Card>
  );
}
