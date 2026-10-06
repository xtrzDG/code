"use client";

import { AnimatedNumber } from "@/components/motion";
import { Badge, Card, EmptyState, ErrorState, LoadingRegion, SkeletonText } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { formatNumber } from "@/lib/format";

import {
  budgetLeftShare,
  budgetTone,
  burnMultiple,
  burnTone,
  hasMeasurements,
  isLatencyOverTarget,
  orderedObjectives,
  overallTone,
  type ErrorBudget,
  type ObjectiveBudget,
} from "../../_lib/errorBudget";
import { formatWait } from "../../_lib/replySpeed";
import { useErrorBudget } from "../../_lib/useErrorBudget";
import { useSystemFormat } from "./useSystemFormat";

const BAR_TONES = { success: "bg-success", warning: "bg-warning", danger: "bg-danger" } as const;

/**
 * The SLOs' error budgets on /admin/system (docs/operations/slo.md): for
 * each ratio objective what is left of its 28-day budget and how fast the
 * last hour burned it, and the answer latency's p95 against 15 s. Hidden
 * from a platform admin whose role may not see operations.
 */
export function ErrorBudgetCard() {
  const { t } = useI18n();
  const budget = useErrorBudget();

  if (budget.error?.status === 403) {
    return null;
  }

  const data = budget.data;
  const tone = data && hasMeasurements(data) ? overallTone(data) : null;
  return (
    <Card
      title={t("adminSystem.errorBudget.title")}
      description={t("adminSystem.errorBudget.description")}
      actions={tone ? <Badge tone={tone}>{t(`adminSystem.errorBudget.states.${tone}`)}</Badge> : undefined}
    >
      {budget.error && !data ? (
        <ErrorState error={budget.error} onRetry={budget.reload} />
      ) : !data ? (
        <LoadingRegion label={t("common.loading")}>
          <SkeletonText lines={4} />
        </LoadingRegion>
      ) : !hasMeasurements(data) ? (
        <EmptyState
          className="py-6"
          title={t("adminSystem.errorBudget.noRows")}
          description={t("adminSystem.errorBudget.noRowsDescription")}
        />
      ) : (
        <ErrorBudgetBody budget={data} />
      )}
    </Card>
  );
}

function ErrorBudgetBody({ budget }: { budget: ErrorBudget }) {
  const { t } = useI18n();
  const format = useSystemFormat();
  return (
    <div className="space-y-4">
      <ul className="grid grid-cols-[minmax(0,1fr)] gap-4 md:grid-cols-3">
        {orderedObjectives(budget).map((objective) => (
          <li key={objective.series} className="min-w-0">
            <ObjectiveTile objective={objective} />
          </li>
        ))}
        <li className="min-w-0">
          <LatencyTile budget={budget} />
        </li>
      </ul>
      <p className="text-xs text-ink-subtle">
        {t("adminSystem.errorBudget.period", {
          since: format.when(budget.measured_since),
          until: format.when(budget.measured_until),
        })}
      </p>
    </div>
  );
}

function ObjectiveTile({ objective }: { objective: ObjectiveBudget }) {
  const { t, locale } = useI18n();
  const name = t(`adminSystem.errorBudget.objectives.${objective.series}`);
  const permille = objective.budget_left_permille;
  const tone = budgetTone(permille);
  const share = budgetLeftShare(permille);
  const percent = (value: number) => formatNumber(value, locale, { style: "percent", maximumFractionDigits: 1 });
  const multiple = burnMultiple(objective.burn_rate_last_hour_percent);

  return (
    <section aria-label={name} className="flex h-full flex-col gap-3 rounded-xl border border-line p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <h3 className="text-sm font-medium text-ink">{name}</h3>
        <span className="text-xs text-ink-muted">
          {t("adminSystem.errorBudget.objective", { objective: percent(objective.objective) })}
        </span>
      </div>
      <p className="text-3xl font-semibold text-ink tabular-nums">
        <AnimatedNumber value={Math.max(0, permille) / 1000} format={(value) => percent(value)} />
      </p>
      <div
        role="meter"
        aria-label={t("adminSystem.errorBudget.meterLabel", { name })}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(share * 100)}
        className="h-2 overflow-hidden rounded-full bg-surface-muted ring-1 ring-line/60"
      >
        <div className={cn("h-full rounded-full", BAR_TONES[tone])} style={{ width: `${share * 100}%` }} />
      </div>
      <p className={cn("text-sm", tone === "danger" ? "text-danger" : "text-ink-muted")}>
        {permille >= 0
          ? t("adminSystem.errorBudget.left", { percent: percent(permille / 1000) })
          : t("adminSystem.errorBudget.overspent", { percent: percent(-permille / 1000) })}
      </p>
      <p className="text-sm text-ink-muted">
        {objective.events > 0
          ? t(`adminSystem.errorBudget.events.${objective.series}`, {
              good: formatNumber(objective.good_events, locale),
              total: formatNumber(objective.events, locale),
            })
          : t(`adminSystem.errorBudget.noEvents.${objective.series}`)}
      </p>
      <div className="mt-auto">
        <Badge tone={burnTone(objective.burn_rate_last_hour_percent)}>
          {t("adminSystem.errorBudget.burn", {
            multiple: formatNumber(multiple, locale, { maximumFractionDigits: 1 }),
          })}
        </Badge>
      </div>
    </section>
  );
}

function LatencyTile({ budget }: { budget: ErrorBudget }) {
  const { t, tp, locale } = useI18n();
  const latency = budget.latency;
  const seconds = (milliseconds: number) => {
    const wait = formatWait(milliseconds, locale);
    return t(`adminReplySpeed.${wait.unit}`, { value: wait.value });
  };
  const isOver = isLatencyOverTarget(budget);

  return (
    <section
      aria-label={t("adminSystem.errorBudget.latency.title")}
      className="flex h-full flex-col gap-3 rounded-xl border border-line p-4"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <h3 className="text-sm font-medium text-ink">{t("adminSystem.errorBudget.latency.title")}</h3>
        <span className="text-xs text-ink-muted">
          {t("adminSystem.errorBudget.latency.objective", { target: seconds(latency.target_ms) })}
        </span>
      </div>
      <p className={cn("text-3xl font-semibold tabular-nums", isOver ? "text-danger" : "text-ink")}>
        {latency.last_hour_p95_ms != null ? seconds(latency.last_hour_p95_ms) : "—"}
      </p>
      <p className="text-sm text-ink-muted">
        {latency.last_hour_p95_ms != null
          ? t("adminSystem.errorBudget.latency.lastHour")
          : t("adminSystem.errorBudget.latency.noLastHour")}
      </p>
      <p className="mt-auto text-sm text-ink-muted">
        {tp("adminSystem.errorBudget.latency.overTarget", latency.hours_over_target, {
          total: formatNumber(latency.measured_hours, locale),
        })}
      </p>
    </section>
  );
}
