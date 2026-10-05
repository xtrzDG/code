"use client";

import { Badge } from "@/components/ui";
import { usageLevel } from "@/lib/usage";
import { useI18n } from "@/i18n/client";
import { formatNumber } from "@/lib/format";

import { clientUsagePercent, type AdminClientSummary } from "../../_lib/clients";

/** A client's package use: minutes and dialogs against the plan, with a badge when near or over. */
export function UsageSummary({ client }: { client: AdminClientSummary }) {
  const { t, locale } = useI18n();
  const percent = clientUsagePercent(client);
  const level = usageLevel(percent);
  return (
    <div className="space-y-1 text-xs text-ink-muted">
      {client.included_voice_minutes > 0 ? (
        <p>
          {t("admin.minutesShort", {
            used: formatNumber(client.used_voice_minutes, locale),
            included: formatNumber(client.included_voice_minutes, locale),
          })}
        </p>
      ) : null}
      <p>
        {t("admin.dialogsShort", {
          used: formatNumber(client.used_dialogs, locale),
          included: formatNumber(client.included_dialogs, locale),
        })}
      </p>
      {level === "warning" || level === "exceeded" ? (
        <Badge tone={level === "exceeded" ? "danger" : "warning"}>
          {formatNumber((percent ?? 0) / 100, locale, { style: "percent" })}
        </Badge>
      ) : null}
    </div>
  );
}
