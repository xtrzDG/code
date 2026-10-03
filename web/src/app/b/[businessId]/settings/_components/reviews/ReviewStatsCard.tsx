"use client";

import type { ReactNode } from "react";

import type { Query } from "@/api/useQuery";
import { IconStar } from "@/components/icons";
import { Card, ErrorState, SkeletonRows } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { formatNumber } from "@/lib/format";

import { answeredShare, scoreBars, type ReviewStatsView } from "../../_lib/reviews";

/**
 * The last 30 days: customers asked, answered (and their share), the
 * average rating, how many opened the review link, and how the ratings
 * spread from 5 to 1.
 */
export function ReviewStatsCard({ stats, isLinkTracked }: { stats: Query<ReviewStatsView>; isLinkTracked: boolean }) {
  const { t } = useI18n();
  return (
    <Card title={t("reviewSettings.stats.title")} description={t("reviewSettings.stats.description")}>
      {stats.error && !stats.data ? (
        <ErrorState error={stats.error} onRetry={stats.reload} className="py-6" />
      ) : !stats.data ? (
        <SkeletonRows rows={2} />
      ) : (
        <StatsBody stats={stats.data} isLinkTracked={isLinkTracked} />
      )}
    </Card>
  );
}

function StatsBody({ stats, isLinkTracked }: { stats: ReviewStatsView; isLinkTracked: boolean }) {
  const { t, tp, locale } = useI18n();
  const number = (value: number) => formatNumber(value, locale);
  const share = answeredShare(stats);
  const average = stats.average_score ?? null;
  return (
    <div className="space-y-6">
      <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Tile label={t("reviewSettings.stats.asked")} value={number(stats.asked_count)} />
        <Tile
          label={t("reviewSettings.stats.answered")}
          value={number(stats.answered_count)}
          note={
            share === null
              ? undefined
              : t("reviewSettings.stats.answeredShare", { percent: formatNumber(share / 100, locale, { style: "percent" }) })
          }
        />
        <Tile
          label={t("reviewSettings.stats.average")}
          value={
            average === null ? (
              <span className="text-base font-medium text-ink-muted">{t("reviewSettings.stats.noAverage")}</span>
            ) : (
              <span className="inline-flex items-center gap-1.5">
                <IconStar className="size-5 fill-current text-warning" aria-hidden />
                {t("reviewSettings.stats.averageValue", {
                  score: formatNumber(average, locale, { minimumFractionDigits: 1, maximumFractionDigits: 1 }),
                })}
              </span>
            )
          }
        />
        <Tile
          label={t("reviewSettings.stats.opened")}
          value={
            isLinkTracked ? (
              number(stats.review_opened_count)
            ) : (
              <span className="text-base font-medium text-ink-muted">{t("reviewSettings.stats.notTracked")}</span>
            )
          }
        />
      </dl>

      <div>
        <h3 className="text-sm font-semibold text-ink">{t("reviewSettings.stats.scores")}</h3>
        <ul className="mt-3 space-y-2">
          {scoreBars(stats).map((bar) => (
            <li key={bar.score} className="flex items-center gap-3 text-sm">
              <span className="sr-only">{tp("reviewSettings.stats.scoreRow", bar.score, { score: bar.score, count: bar.count })}</span>
              <span aria-hidden className="inline-flex w-8 shrink-0 items-center gap-1 tabular-nums text-ink">
                {number(bar.score)}
                <IconStar className="size-3.5 text-ink-muted" />
              </span>
              <span aria-hidden className="h-2 min-w-0 flex-1 overflow-hidden rounded-full bg-surface-muted">
                <span className="block h-full rounded-full bg-accent" style={{ width: `${bar.share}%` }} />
              </span>
              <span aria-hidden className="w-10 shrink-0 text-end tabular-nums text-ink-muted">
                {number(bar.count)}
              </span>
            </li>
          ))}
        </ul>
      </div>

      {stats.skipped_count > 0 || stats.failed_count > 0 ? (
        <p className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-ink-muted">
          {stats.skipped_count > 0 ? <span>{t("reviewSettings.stats.notAsked", { count: number(stats.skipped_count) })}</span> : null}
          {stats.failed_count > 0 ? (
            <span>{t("reviewSettings.stats.notDelivered", { count: number(stats.failed_count) })}</span>
          ) : null}
        </p>
      ) : null}
    </div>
  );
}

function Tile({ label, value, note }: { label: string; value: ReactNode; note?: string | undefined }) {
  return (
    <div className="min-w-0 rounded-xl border border-line p-4">
      <dt className="text-sm text-ink-muted">{label}</dt>
      <dd className="mt-1 text-2xl font-semibold text-ink tabular-nums [overflow-wrap:anywhere]">{value}</dd>
      {note ? <dd className="mt-0.5 text-sm text-ink-muted">{note}</dd> : null}
    </div>
  );
}
