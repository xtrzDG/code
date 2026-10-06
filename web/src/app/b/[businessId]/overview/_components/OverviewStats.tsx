"use client";

/**
 * The period's statistics on the Overview: the tiles, the chart by day,
 * the package, languages, channels, bookings by status and why
 * conversations went to a person. Until the period has any activity, one
 * empty card instead of a wall of zeros. On a phone each block is a folded
 * row (PhoneFold) with its leading number; large screens show them all.
 */

import type { Schema } from "@/api/types";
import { useBusinessFormat } from "@/components/business/BusinessContext";
import { formatLocalDate, formatLocalDateRange } from "@/components/insights/dates";
import { BOOKING_STATUS, CHANNEL_LABELS, HANDOFF_REASONS } from "@/components/insights/labels";
import { formatPercent } from "@/components/insights/numbers";
import { Button, Card, EmptyState } from "@/components/ui";
import type { ValueModel } from "@/components/value/valueModel";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { languageName } from "@/lib/format";

import { BarList } from "./DashboardWidgets";
import { toBars, type Bar } from "./dashboardModel";
import { PackageCard } from "./PackageCard";
import { PeriodTiles } from "./PeriodTiles";
import { PhoneFold } from "./PhoneFold";
import { TrendChart } from "./TrendChart";

const SHORT_DATE: Intl.DateTimeFormatOptions = { day: "numeric", month: "short" };

type DashboardStats = Schema<"DashboardStats">;

export function OverviewStats({
  data,
  value,
  isPlaceholder,
  hasError,
  onRetry,
}: {
  data: DashboardStats;
  value: ValueModel | undefined;
  isPlaceholder: boolean;
  /** A newer period failed to load (the shown one stays). */
  hasError: boolean;
  onRetry: () => void;
}) {
  const { t, locale } = useI18n();
  const format = useBusinessFormat();
  const hasActivity = data.conversation_count + data.booking_count + data.lead_count + data.handoff_count > 0;
  const barValue = (count: number, percent: number) =>
    t("dashboard.breakdown.value", { count: format.number(count), percent: formatPercent(percent, locale) });
  /** The folded row's summary: the leading item and its share. */
  const leading = <Key extends string>(bars: readonly Bar<Key>[], labelOf: (key: Key) => string) =>
    bars[0] ? t("overviewPhone.folds.summary", { label: labelOf(bars[0].key), value: formatPercent(bars[0].percent, locale) }) : null;

  const languages = toBars((data.languages ?? []).map((item) => ({ key: item.language, count: item.count })));
  const channels = toBars((data.channels ?? []).map((item) => ({ key: item.channel, count: item.count })));
  const bookings = toBars((data.bookings_by_status ?? []).map((item) => ({ key: item.status, count: item.count })));
  const handoffs = toBars((data.handoffs_by_reason ?? []).map((item) => ({ key: item.reason, count: item.count })));
  const languageOf = (tag: string) => languageName(tag, locale);
  const channelOf = (channel: (typeof channels)[number]["key"]) => t(CHANNEL_LABELS[channel]);

  return (
    <section aria-labelledby="dashboard-period" className={cn("animate-settle space-y-4 transition-opacity", isPlaceholder && "opacity-60")}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="dashboard-period" className="text-sm font-semibold tracking-wide text-ink-muted uppercase">
          {data.is_since_launch
            ? t("dashboard.periodSince", { date: formatLocalDate(data.date_from, locale, SHORT_DATE) })
            : t("dashboard.periodRange", { range: formatLocalDateRange(data.date_from, data.date_to, locale) })}
        </h2>
        {hasError ? (
          <Button variant="ghost" size="sm" onClick={onRetry}>
            {t("common.retry")}
          </Button>
        ) : null}
      </div>

      {hasActivity ? (
        <>
          <PhoneFold
            name="statistics"
            title={t("overviewPhone.folds.statistics")}
            summary={t("overviewPhone.folds.summary", { label: t("dashboard.kpi.conversations"), value: format.number(data.conversation_count) })}
          >
            <div className="max-lg:p-3 lg:contents">
              <PeriodTiles data={data} value={value} isBusy={isPlaceholder} />
            </div>
          </PhoneFold>

          {(data.daily ?? []).length > 1 ? (
            <PhoneFold name="trend" title={t("dashboard.trend.title")}>
              <TrendChart days={data.daily ?? []} />
            </PhoneFold>
          ) : null}

          <div className="grid gap-4 lg:grid-cols-3">
            <PhoneFold name="package" title={t("dashboard.usage.title")}>
              <PackageCard usage={data.package ?? null} periodVoiceMinutes={data.used_voice_minutes} />
            </PhoneFold>
            <div className="grid gap-4 sm:grid-cols-2 lg:col-span-2">
              <PhoneFold name="languages" title={t("dashboard.breakdown.languages")} summary={leading(languages, languageOf)}>
                <BarList
                  title={t("dashboard.breakdown.languages")}
                  bars={languages}
                  labelOf={languageOf}
                  valueOf={(bar) => barValue(bar.count, bar.percent)}
                  emptyText={t("dashboard.breakdown.empty")}
                />
              </PhoneFold>
              <PhoneFold name="channels" title={t("dashboard.breakdown.channels")} summary={leading(channels, channelOf)}>
                <BarList
                  title={t("dashboard.breakdown.channels")}
                  bars={channels}
                  labelOf={channelOf}
                  valueOf={(bar) => barValue(bar.count, bar.percent)}
                  emptyText={t("dashboard.breakdown.empty")}
                />
              </PhoneFold>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <PhoneFold name="bookings" title={t("dashboard.breakdown.bookingsByStatus")} summary={format.number(data.booking_count)}>
              <BarList
                title={t("dashboard.breakdown.bookingsByStatus")}
                bars={bookings}
                labelOf={(status) => t(BOOKING_STATUS[status].label)}
                valueOf={(bar) => format.number(bar.count)}
                emptyText={t("dashboard.breakdown.empty")}
              />
            </PhoneFold>
            <PhoneFold name="handoffs" title={t("dashboard.breakdown.handoffsByReason")} summary={format.number(data.handoff_count)}>
              <BarList
                title={t("dashboard.breakdown.handoffsByReason")}
                bars={handoffs}
                labelOf={(reason) => t(HANDOFF_REASONS[reason])}
                valueOf={(bar) => format.number(bar.count)}
                emptyText={t("dashboard.breakdown.empty")}
              />
            </PhoneFold>
          </div>
        </>
      ) : (
        // Nothing yet in the period: one card instead of a wall of zeros.
        <div className="grid gap-4 lg:grid-cols-3">
          <PackageCard usage={data.package ?? null} periodVoiceMinutes={data.used_voice_minutes} />
          <Card className="lg:col-span-2" data-stats-empty="">
            <EmptyState
              title={t(data.is_since_launch ? "dashboard.statsEmptyTitle" : "dashboard.emptyTitle")}
              description={t(data.is_since_launch ? "dashboard.statsEmptyDescription" : "dashboard.emptyDescription")}
            />
          </Card>
        </div>
      )}
    </section>
  );
}
