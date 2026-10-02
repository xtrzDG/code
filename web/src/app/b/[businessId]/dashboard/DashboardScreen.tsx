"use client";

import { useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { sectionQueries } from "@/api/sectionQueries";
import { useQuery } from "@/api/useQuery";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { BusinessStatusBadge } from "@/components/business/BusinessStatusBadge";
import { IconBook, IconHandoff } from "@/components/icons";
import { formatLocalDateRange } from "@/components/insights/dates";
import { useToday } from "@/components/insights/useToday";
import { BOOKING_STATUS, CHANNEL_LABELS, HANDOFF_REASONS } from "@/components/insights/labels";
import { formatPercent } from "@/components/insights/numbers";
import { SegmentedControl } from "@/components/insights/SegmentedControl";
import { replaceUrlQuery } from "@/components/insights/urlQuery";
import { Button, Card, EmptyState, ErrorState, LoadingRegion, PageHeader } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { languageName } from "@/lib/format";
import { businessPath } from "@/lib/navigation";

import { DashboardPeriodSkeleton } from "./_components/DashboardSkeleton";
import { AttentionTile, BarList, NextStepCard, StatTile } from "./_components/DashboardWidgets";
import {
  canTakeStep,
  DASHBOARD_PERIODS,
  DEFAULT_DASHBOARD_PERIOD,
  nextStep,
  periodRange,
  toBars,
  type DashboardPeriod,
} from "./_components/dashboardModel";
import { PackageCard } from "./_components/PackageCard";
import { TrendChart } from "./_components/TrendChart";

/**
 * The dashboard (concept /dashboard): what to do next, what waits for a
 * person, requests, bookings, after-hours share, languages, channels,
 * handoffs and the package usage, for a period in the business time zone.
 */
export function DashboardScreen({ initialPeriod }: { initialPeriod: DashboardPeriod | null }) {
  const { t, tp, locale } = useI18n();
  const { business, isOwner } = useBusiness();
  const format = useBusinessFormat();
  const [period, setPeriod] = useState<DashboardPeriod>(initialPeriod ?? DEFAULT_DASHBOARD_PERIOD);
  const today = useToday(business.timezone);
  const range = periodRange(period, today);
  const businessId = business.id;

  const statsQuery = sectionQueries.dashboardStats(businessId, range.from, range.to);
  // Another period keeps the shown tiles (dimmed) until its numbers arrive.
  const stats = useQuery(statsQuery.key, statsQuery.fetch, { keepPreviousData: true });
  // Only the count of open handoffs is needed: one item, the totals come along.
  const openHandoffs = useQuery(queryKeys.handoffs.openCount(businessId), () =>
    api.GET("/v1/businesses/{business_id}/handoffs", {
      params: { path: { business_id: businessId }, query: { is_open: "true", limit: "1" } },
    }),
  );
  const gaps = useQuery(
    queryKeys.profile.gaps(businessId, locale),
    () =>
      api.GET("/v1/businesses/{business_id}/profile/gaps", {
        params: { path: { business_id: businessId }, query: { language: locale } },
      }),
    { enabled: business.status === "onboarding" },
  );

  const choosePeriod = (value: DashboardPeriod) => {
    setPeriod(value);
    replaceUrlQuery(value === DEFAULT_DASHBOARD_PERIOD ? "" : `period=${value}`);
  };

  const step = nextStep(business);
  const missingCount = (gaps.data?.gaps ?? []).filter((gap) => gap.is_blocking).length ?? 0;
  const openHandoffCount = openHandoffs.data?.open_count;
  const data = stats.data;
  const hasActivity =
    data !== undefined &&
    data.conversation_count + data.booking_count + data.lead_count + data.handoff_count > 0;

  return (
    <>
      <PageHeader
        title={t("nav.dashboard")}
        description={t("pages.dashboard.description")}
        actions={
          <SegmentedControl
            label={t("dashboard.periodLabel")}
            value={period}
            onChange={choosePeriod}
            options={DASHBOARD_PERIODS.map((value) => ({ value, label: t(`dashboard.periods.${value}`) }))}
          />
        }
      />

      <div className="space-y-6">
        <NextStepCard
          step={step}
          status={<BusinessStatusBadge status={business.status} />}
          href={canTakeStep(step, isOwner) ? businessPath(businessId, step.section) : null}
          note={
            business.status === "onboarding" && missingCount > 0
              ? tp("dashboard.status.onboarding.missing", missingCount)
              : null
          }
        />

        <section aria-labelledby="dashboard-attention" className="space-y-3">
          <h2 id="dashboard-attention" className="text-sm font-semibold tracking-wide text-ink-muted uppercase">
            {t("dashboard.attention.title")}
          </h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <AttentionTile
              href={businessPath(businessId, "handoffs")}
              label={t("dashboard.attention.openHandoffs")}
              hint={t("dashboard.attention.openHandoffsHint")}
              count={openHandoffCount === undefined ? "–" : format.number(openHandoffCount)}
              actionLabel={t("dashboard.attention.open")}
              icon={<IconHandoff className="size-5" />}
            />
            <AttentionTile
              href={businessPath(businessId, "knowledge")}
              label={t("dashboard.attention.questions")}
              hint={t("dashboard.attention.questionsHint")}
              count={data === undefined ? "–" : format.number(data.open_unanswered_question_count)}
              actionLabel={t("dashboard.attention.open")}
              icon={<IconBook className="size-5" />}
            />
          </div>
        </section>

        {stats.error && !data ? (
          <Card>
            <ErrorState error={stats.error} onRetry={stats.reload} />
          </Card>
        ) : !data ? (
          <LoadingRegion label={t("dashboard.loading")}>
            <DashboardPeriodSkeleton />
          </LoadingRegion>
        ) : (
          <section
            aria-labelledby="dashboard-period"
            className={stats.isPlaceholder ? "space-y-4 opacity-60 transition-opacity" : "animate-settle space-y-4"}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 id="dashboard-period" className="text-sm font-semibold tracking-wide text-ink-muted uppercase">
                {t("dashboard.periodRange", { range: formatLocalDateRange(data.date_from, data.date_to, locale) })}
              </h2>
              {stats.error ? (
                <Button variant="ghost" size="sm" onClick={stats.reload}>
                  {t("common.retry")}
                </Button>
              ) : null}
            </div>

            <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3" aria-busy={stats.isPlaceholder || undefined}>
              <StatTile
                label={t("dashboard.kpi.conversations")}
                value={format.number(data.conversation_count)}
                hint={t("dashboard.kpi.conversationsHint")}
              />
              <StatTile label={t("dashboard.kpi.messages")} value={format.number(data.customer_message_count)} />
              <StatTile label={t("dashboard.kpi.bookings")} value={format.number(data.booking_count)} />
              <StatTile
                label={t("dashboard.kpi.afterHours")}
                value={formatPercent(data.after_hours_share_percent, locale)}
                hint={t("dashboard.kpi.afterHoursHint", {
                  count: format.number(data.after_hours_conversation_count),
                  total: format.number(data.conversation_count),
                })}
              />
              <StatTile label={t("dashboard.kpi.leads")} value={format.number(data.lead_count)} />
              <StatTile label={t("dashboard.kpi.handoffs")} value={format.number(data.handoff_count)} />
            </dl>

            {hasActivity && (data.daily ?? []).length > 1 ? <TrendChart days={data.daily ?? []} /> : null}

            <div className="grid gap-4 lg:grid-cols-3">
              <PackageCard usage={data.package ?? null} periodVoiceMinutes={data.used_voice_minutes} />
              {hasActivity ? (
                <div className="grid gap-4 sm:grid-cols-2 lg:col-span-2">
                  <BarList
                    title={t("dashboard.breakdown.languages")}
                    bars={toBars((data.languages ?? []).map((item) => ({ key: item.language, count: item.count })))}
                    labelOf={(tag) => languageName(tag, locale)}
                    valueOf={(bar) => barValue(bar.count, bar.percent)}
                    emptyText={t("dashboard.breakdown.empty")}
                  />
                  <BarList
                    title={t("dashboard.breakdown.channels")}
                    bars={toBars((data.channels ?? []).map((item) => ({ key: item.channel, count: item.count })))}
                    labelOf={(channel) => t(CHANNEL_LABELS[channel])}
                    valueOf={(bar) => barValue(bar.count, bar.percent)}
                    emptyText={t("dashboard.breakdown.empty")}
                  />
                </div>
              ) : (
                <Card className="lg:col-span-2">
                  <EmptyState title={t("dashboard.emptyTitle")} description={t("dashboard.emptyDescription")} />
                </Card>
              )}
            </div>

            {hasActivity ? (
              <div className="grid gap-4 sm:grid-cols-2">
                <BarList
                  title={t("dashboard.breakdown.bookingsByStatus")}
                  bars={toBars((data.bookings_by_status ?? []).map((item) => ({ key: item.status, count: item.count })))}
                  labelOf={(status) => t(BOOKING_STATUS[status].label)}
                  valueOf={(bar) => format.number(bar.count)}
                  emptyText={t("dashboard.breakdown.empty")}
                />
                <BarList
                  title={t("dashboard.breakdown.handoffsByReason")}
                  bars={toBars((data.handoffs_by_reason ?? []).map((item) => ({ key: item.reason, count: item.count })))}
                  labelOf={(reason) => t(HANDOFF_REASONS[reason])}
                  valueOf={(bar) => format.number(bar.count)}
                  emptyText={t("dashboard.breakdown.empty")}
                />
              </div>
            ) : null}
          </section>
        )}
      </div>
    </>
  );

  function barValue(count: number, percent: number): string {
    return t("dashboard.breakdown.value", { count: format.number(count), percent: formatPercent(percent, locale) });
  }
}
