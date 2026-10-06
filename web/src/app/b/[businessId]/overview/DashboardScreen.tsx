"use client";

import { useState } from "react";

import { sectionQueries } from "@/api/sectionQueries";
import { useQuery } from "@/api/useQuery";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { useAttentionCounts } from "@/components/shell/LiveEvents";
import { BusinessStatusBadge } from "@/components/business/BusinessStatusBadge";
import { IconBook, IconHandoff } from "@/components/icons";
import { useToday } from "@/components/insights/useToday";
import { SegmentedControl } from "@/components/insights/SegmentedControl";
import { replaceUrlQuery } from "@/components/insights/urlQuery";
import { Card, ErrorState, LoadingRegion, PageHeader } from "@/components/ui";
import { useSetupProgress } from "@/components/setupGuide/useSetupProgress";
import { AnswersToImproveCard } from "@/components/teaching/AnswersToImproveCard";
import { useValueOfDates } from "@/components/value/useValueQueries";
import { useI18n } from "@/i18n/client";
import { businessPath, inboxPath } from "@/lib/navigation";
import { guideCard } from "@/lib/setupGuide/guide";

import { DashboardPeriodSkeleton } from "./_components/DashboardSkeleton";
import { AttentionTile, NextStepCard } from "./_components/DashboardWidgets";
import { InviteCard } from "./_components/InviteCard";
import {
  canTakeStep,
  DASHBOARD_PERIODS,
  DEFAULT_DASHBOARD_PERIOD,
  isLaunched,
  needsStatusCard,
  nextStep,
  periodRange,
  type DashboardPeriod,
} from "./_components/dashboardModel";
import { OverviewStats } from "./_components/OverviewStats";
import { PhoneFold, PhoneFolds } from "./_components/PhoneFold";
import { SetupGuideCard } from "./_components/setupGuide/SetupGuideCard";
import { TodayBlock } from "./_components/TodayBlock";
import { TodayQueue } from "./_components/TodayQueue";
import { TopicsCard } from "./_components/TopicsCard";
import { ValueHero } from "./_components/ValueHero";

/**
 * The dashboard (concept /dashboard): what to do next, what waits for a
 * person, requests, bookings, after-hours share, languages, channels,
 * handoffs and the package usage, for a period in the business time zone
 * (never from before the launch: "since 5 Oct"). Until a period has any
 * activity its statistics are one empty card, not a wall of zeros.
 *
 * On a phone the Today block comes first (who waits for a person, today's
 * bookings, questions without an answer), then the value hero; the
 * statistics and the topics fold into rows that open on a tap (PhoneFold,
 * remembered per person). Large screens keep the tiles and every block.
 */
export function DashboardScreen({ initialPeriod }: { initialPeriod: DashboardPeriod | null }) {
  const { t } = useI18n();
  const { business, isOwner } = useBusiness();
  const format = useBusinessFormat();
  const [period, setPeriod] = useState<DashboardPeriod>(initialPeriod ?? DEFAULT_DASHBOARD_PERIOD);
  const today = useToday(business.timezone);
  const range = periodRange(period, today);
  const businessId = business.id;

  const statsQuery = sectionQueries.dashboardStats(businessId, range.from, range.to);
  // Another period keeps the shown tiles (dimmed) until its numbers arrive.
  const stats = useQuery(statsQuery.key, statsQuery.fetch, { keepPreviousData: true });
  // The same dates in the value model: changes against the period before, and the owner's hero.
  const value = useValueOfDates(businessId, range.from, range.to);
  // The badges' counts: no list of handoffs is loaded (that would be an audited view).
  const inbox = useAttentionCounts();
  // The setup guide (owners): before the launch the way back into the setup,
  // after it the way to the first customers.
  const setup = useSetupProgress(businessId, { enabled: isOwner });
  const guide = guideCard(setup.data, isOwner);

  const choosePeriod = (value: DashboardPeriod) => {
    setPeriod(value);
    replaceUrlQuery(value === DEFAULT_DASHBOARD_PERIOD ? "" : `period=${value}`);
  };

  const step = nextStep(business);
  const data = stats.data;
  // Value first once customers are served (tests in the sandbox count for nothing).
  const showsValue = isOwner && (business.status === "live" || business.status === "paused");

  return (
    <PhoneFolds>
      <PageHeader
        title={t("navigation.pages.overviewDashboard")}
        actions={
          <SegmentedControl
            label={t("dashboard.periodLabel")}
            value={period}
            onChange={choosePeriod}
            options={DASHBOARD_PERIODS.map((value) => ({ value, label: t(`dashboard.periods.${value}`) }))}
          />
        }
      />

      <div className="space-y-6 max-lg:space-y-4">
        {/* Phones: today's work before anything else. */}
        <TodayBlock unansweredQuestions={data?.open_unanswered_question_count} className="lg:hidden" />

        {showsValue && value.data ? <ValueHero model={value.data} isPlaceholder={value.isPlaceholder} /> : null}

        {needsStatusCard(business, isOwner) || setup.error ? (
          <NextStepCard
            step={step}
            status={<BusinessStatusBadge status={business.status} />}
            href={canTakeStep(step, isOwner) ? businessPath(businessId, step.page) : null}
          />
        ) : null}

        {guide !== "hidden" && setup.data ? <SetupGuideCard setup={setup.data} isFinished={guide === "finished"} /> : null}

        {/* Large screens: the attention tiles (phones have them in Today). */}
        {isOwner ? (
          <section aria-labelledby="dashboard-attention" className="space-y-3 max-lg:hidden">
            <h2 id="dashboard-attention" className="text-sm font-semibold tracking-wide text-ink-muted uppercase">
              {t("dashboard.attention.title")}
            </h2>
            <div className="grid gap-3 sm:grid-cols-2">
              <AttentionTile
                href={inboxPath(businessId, "needs_person")}
                label={t("dashboard.attention.openHandoffs")}
                hint={t("dashboard.attention.openHandoffsHint")}
                count={inbox?.needsPerson}
                formatCount={format.number}
                actionLabel={t("dashboard.attention.open")}
                icon={<IconHandoff className="size-5" />}
              />
              <AttentionTile
                href={businessPath(businessId, "assistant/knowledge")}
                label={t("dashboard.attention.questions")}
                hint={t("dashboard.attention.questionsHint")}
                count={data?.open_unanswered_question_count}
                formatCount={format.number}
                actionLabel={t("dashboard.attention.open")}
                icon={<IconBook className="size-5" />}
              />
            </div>
          </section>
        ) : (
          <div className="max-lg:hidden">
            <TodayQueue />
          </div>
        )}

        {stats.error && !data ? (
          <Card>
            <ErrorState error={stats.error} onRetry={stats.reload} />
          </Card>
        ) : !data ? (
          <LoadingRegion label={t("dashboard.loading")}>
            <DashboardPeriodSkeleton />
          </LoadingRegion>
        ) : (
          <OverviewStats
            data={data}
            value={value.data}
            isPlaceholder={stats.isPlaceholder}
            hasError={Boolean(stats.error)}
            onRetry={stats.reload}
          />
        )}

        {/* Bad ratings and questions without an answer, to fix while they are fresh. */}
        {isLaunched(business.status) ? (
          <PhoneFold name="answers" title={t("teaching.improve.title")}>
            <AnswersToImproveCard />
          </PhoneFold>
        ) : null}

        {/* What customers asked about in the last 30 days (the period above does not change it). */}
        {isLaunched(business.status) ? (
          <PhoneFold name="topics" title={t("topics.title")}>
            <TopicsCard />
          </PhoneFold>
        ) : null}

        {/* "Invite a business — a month free", from the tenth booking (owners), after everything above, on every screen. */}
        {isOwner ? <InviteCard /> : null}
      </div>
    </PhoneFolds>
  );
}
