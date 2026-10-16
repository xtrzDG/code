"use client";

import { sectionQueries } from "@/api/sectionQueries";
import { useQuery } from "@/api/useQuery";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import type { DashboardPackageUsage } from "@/components/insights/types";
import { Alert, ButtonLink, Card } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath, setupPath } from "@/lib/navigation";
import { isUsageWarned, usageLevel } from "@/lib/usage";

import { Meter } from "./DashboardWidgets";
import { isLaunched } from "./dashboardModel";

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
  const voiceLevel = usageLevel(usage?.voice_usage_percent);
  const dialogLevel = usageLevel(usage?.dialog_usage_percent);
  const isWarned = isUsageWarned(voiceLevel) || isUsageWarned(dialogLevel);
  const needsPrice = isOwner && usage !== null && isWarned;
  const beforeLaunch = usage === null && !isLaunched(business.status);

  const billingQuery = sectionQueries.billingOverview(businessId, locale);
  const billing = useQuery(billingQuery.key, billingQuery.fetch, { enabled: needsPrice || (isOwner && beforeLaunch) });
  const prices = billing.data?.usage ?? null;
  // Before the launch the trial starts by itself, unless the billing says otherwise (a trial already used).
  const trialAtLaunch = beforeLaunch && billing.data?.does_trial_start_at_go_live !== false;

  if (!usage) {
    return (
      <Card title={t("dashboard.usage.title")}>
        <div className="space-y-3">
          <p className="text-sm font-medium text-ink">
            {t(trialAtLaunch ? "dashboard.usage.trialAtLaunchTitle" : "dashboard.usage.noPlanTitle")}
          </p>
          <p className="text-sm text-ink-muted">
            {trialAtLaunch
              ? t("dashboard.usage.trialAtLaunchDescription")
              : t(isOwner ? "dashboard.usage.noPlanDescription" : "dashboard.usage.noPlanStaff")}
          </p>
          {isOwner ? (
            <ButtonLink
              href={trialAtLaunch ? setupPath(businessId) : businessPath(businessId, "settings/billing")}
              variant="secondary"
              size="sm"
            >
              {t(trialAtLaunch ? "dashboard.continueSetup" : "dashboard.usage.toBilling")}
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
        ) : isWarned ? (
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
