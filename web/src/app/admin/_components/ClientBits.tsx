"use client";

import { Badge } from "@/components/ui";
import { formatMicroUsd } from "@/components/workspace/helpers";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { formatMoney } from "@/lib/format";

import { HEALTH_TONES, isCriticalIssue, type AdminClientSummary, type ClientHealthIssue, type ClientHealthStatus } from "../_lib/clients";
import { HEALTH_LABELS, ISSUE_LABELS } from "./labels";

export function HealthBadge({ status }: { status: ClientHealthStatus }) {
  const { t } = useI18n();
  return <Badge tone={HEALTH_TONES[status]}>{t(HEALTH_LABELS[status])}</Badge>;
}

/** The reasons a client needs attention; critical ones in red. `limit` shows "+N" for the rest. */
export function IssueChips({ issues, limit }: { issues: readonly ClientHealthIssue[]; limit?: number }) {
  const { t } = useI18n();
  const shown = limit === undefined ? issues : issues.slice(0, limit);
  const rest = issues.length - shown.length;
  return (
    <ul className="flex flex-wrap gap-1.5">
      {shown.map((issue) => (
        <li key={issue}>
          <Badge tone={isCriticalIssue(issue) ? "danger" : "neutral"}>{t(ISSUE_LABELS[issue])}</Badge>
        </li>
      ))}
      {rest > 0 ? (
        <li>
          <Badge>+{rest}</Badge>
        </li>
      ) : null}
    </ul>
  );
}

/** Provider cost in money when converted, else in US dollars from micro units. */
export function ProviderCost({ cost, className }: { cost: AdminClientSummary["cost"]; className?: string }) {
  const { locale } = useI18n();
  return (
    <span className={className}>
      {cost.provider_cost
        ? formatMoney(cost.provider_cost.amount_minor, cost.provider_cost.currency_code, locale)
        : formatMicroUsd(cost.provider_cost_micro_usd, locale)}
    </span>
  );
}

/** Margin with its percentage; red for a loss, a dash when no rate is known. */
export function Margin({ cost, className }: { cost: AdminClientSummary["cost"]; className?: string }) {
  const { t, locale } = useI18n();
  if (!cost.margin) {
    return <span className={cn("text-ink-subtle", className)}>{t("admin.unknown")}</span>;
  }
  const isLoss = cost.margin.amount_minor < 0;
  return (
    <span className={cn(isLoss ? "text-danger" : "text-ink", className)}>
      {formatMoney(cost.margin.amount_minor, cost.margin.currency_code, locale)}
      {cost.margin_percent !== null && cost.margin_percent !== undefined ? (
        <span className="ml-1 text-xs opacity-80">
          ({new Intl.NumberFormat(locale, { style: "percent", maximumFractionDigits: 1 }).format(cost.margin_percent / 100)})
        </span>
      ) : null}
    </span>
  );
}
