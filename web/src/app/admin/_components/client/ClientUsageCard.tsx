"use client";

import { Card } from "@/components/ui";
import { usagePercent } from "@/components/workspace/helpers";
import { UsageMeter } from "@/components/workspace/UsageMeter";
import { useI18n } from "@/i18n/client";
import { formatNumber } from "@/lib/format";

import type { AdminClientSummary } from "../../_lib/clients";

/** Voice minutes and dialogs used of the plan. */
export function ClientUsageCard({ summary }: { summary: AdminClientSummary }) {
  const { t, locale } = useI18n();
  return (
    <Card title={t("admin.detail.usageTitle")}>
      <div className="space-y-5">
        {summary.included_voice_minutes > 0 || summary.used_voice_minutes > 0 ? (
          <UsageMeter
            label={t("billing.usage.voice")}
            usedText={t("billing.usage.minutesOf", {
              used: formatNumber(summary.used_voice_minutes, locale),
              included: formatNumber(summary.included_voice_minutes, locale),
            })}
            percent={usagePercent(summary.used_voice_minutes, summary.included_voice_minutes)}
          />
        ) : null}
        <UsageMeter
          label={t("billing.usage.dialogs")}
          usedText={t("billing.usage.dialogsOf", {
            used: formatNumber(summary.used_dialogs, locale),
            included: formatNumber(summary.included_dialogs, locale),
          })}
          percent={usagePercent(summary.used_dialogs, summary.included_dialogs)}
        />
      </div>
    </Card>
  );
}
