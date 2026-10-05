"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { CHANNEL_LABELS } from "@/components/insights/labels";
import { Alert, Badge, Card, ErrorState, Skeleton, Table, TBody, Td, Th, THead, Tr } from "@/components/ui";
import { Facts } from "@/components/workspace/Facts";
import { useI18n } from "@/i18n/client";
import { formatScore, scoreTone } from "@/lib/assistant/autotests";
import { cn } from "@/lib/cn";
import { formatNumber, languageName } from "@/lib/format";

import { barHeight, hasWeekComparison, judgedDays, weakCriteria, type ClientQuality, type QualityDay } from "../../_lib/quality";
import { useClientFormat } from "../../_lib/useClientFormat";
import { CRITERION_LABELS } from "../labels";

const BAR_TONES = { success: "bg-success", warning: "bg-warning", danger: "bg-danger" } as const;

/**
 * The client's production quality (GET /v1/admin/clients/{business_id}/quality):
 * the nightly judge's average per day for 30 days, the last week against
 * the one before, and the lowest-scored conversations (scores only).
 */
export function QualityCard({ businessId, timeZone }: { businessId: string; timeZone: string }) {
  const { t } = useI18n();
  const quality = useQuery(queryKeys.admin.clientQuality(businessId), () =>
    api.GET("/v1/admin/clients/{business_id}/quality", { params: { path: { business_id: businessId } } }),
  );

  return (
    <Card title={t("quality.admin.title")} description={t("quality.admin.description")}>
      {quality.error && !quality.data ? (
        <ErrorState error={quality.error} onRetry={quality.reload} />
      ) : !quality.data ? (
        <Skeleton className="h-40 w-full" />
      ) : quality.data.sample_count === 0 ? (
        <p className="text-sm text-ink-muted">{t("quality.admin.empty")}</p>
      ) : (
        <QualityDetails quality={quality.data} timeZone={timeZone} />
      )}
    </Card>
  );
}

function QualityDetails({ quality, timeZone }: { quality: ClientQuality; timeZone: string }) {
  const { t, locale } = useI18n();
  const format = useClientFormat(timeZone);
  const score = (value: number) => t("quality.admin.scoreValue", { score: formatScore(value, locale) });
  const lowest = quality.lowest ?? [];

  return (
    <div className="space-y-5">
      <Facts
        columns={3}
        items={[
          {
            label: t("quality.admin.average"),
            value: quality.average_score !== null && quality.average_score !== undefined ? score(quality.average_score) : "—",
          },
          {
            label: t("quality.admin.lastWeek"),
            value: (
              <span className="flex flex-wrap items-center gap-2">
                <span>{quality.last_week_average !== null && quality.last_week_average !== undefined ? score(quality.last_week_average) : "—"}</span>
                {quality.is_dropping ? <Badge tone="danger">{t("quality.admin.dropping", { percent: quality.drop_percent })}</Badge> : null}
                {hasWeekComparison(quality) && quality.previous_week_average !== null && quality.previous_week_average !== undefined ? (
                  <span className="text-xs font-normal text-ink-subtle">
                    {t("quality.admin.previousWeek", { score: formatScore(quality.previous_week_average, locale) })}
                  </span>
                ) : null}
              </span>
            ),
          },
          { label: t("quality.admin.judged"), value: <span className="tabular-nums">{formatNumber(quality.sample_count, locale)}</span> },
        ]}
      />
      {quality.is_dropping ? <Alert tone="warning">{t("quality.admin.droppingNote", { percent: quality.drop_percent })}</Alert> : null}

      <TrendBars days={quality.days} dayLabel={(day) => format.date(day.day_start)} />

      {lowest.length > 0 ? (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-ink">{t("quality.admin.lowestTitle")}</h3>
          <div className="overflow-x-auto rounded-xl border border-line">
            <Table caption={t("quality.admin.lowestCaption")}>
              <THead>
                <Tr>
                  <Th>{t("quality.admin.judgedAt")}</Th>
                  <Th>{t("quality.admin.channel")}</Th>
                  <Th>{t("quality.admin.language")}</Th>
                  <Th align="right">{t("quality.admin.score")}</Th>
                  <Th>{t("quality.admin.weak")}</Th>
                </Tr>
              </THead>
              <TBody>
                {lowest.map((sample) => {
                  const weak = weakCriteria(sample);
                  return (
                    <Tr key={sample.conversation_id}>
                      <Td className="whitespace-nowrap">{format.dateTime(sample.judged_at)}</Td>
                      <Td>{t(CHANNEL_LABELS[sample.channel])}</Td>
                      <Td>{sample.language ? languageName(sample.language, locale) : "—"}</Td>
                      <Td align="right" className="whitespace-nowrap tabular-nums">
                        <Badge tone={scoreTone(sample.average_score)}>{formatScore(sample.average_score, locale)}</Badge>
                      </Td>
                      <Td className="text-ink-muted">
                        {weak.length > 0 ? weak.map((criterion) => t(CRITERION_LABELS[criterion])).join(", ") : t("quality.admin.noWeak")}
                      </Td>
                    </Tr>
                  );
                })}
              </TBody>
            </Table>
          </div>
        </div>
      ) : null}
    </div>
  );
}

/** One bar per day, colored by score; the same numbers as a table behind a disclosure. */
function TrendBars({ days, dayLabel }: { days: readonly QualityDay[]; dayLabel: (day: QualityDay) => string }) {
  const { t, locale } = useI18n();
  const rows = judgedDays(days);
  return (
    <div>
      <p className="mb-2 text-xs text-ink-subtle">{t("quality.admin.trendLabel")}</p>
      <div className="flex h-24 items-end gap-0.5 rounded-lg bg-surface-muted/60 px-1 pt-1" aria-hidden>
        {days.map((day) => {
          const height = barHeight(day.average_score);
          const label =
            height === null || day.average_score === null || day.average_score === undefined
              ? t("quality.admin.noScoresDay", { date: dayLabel(day) })
              : t("quality.admin.dayValue", { date: dayLabel(day), score: formatScore(day.average_score, locale), count: day.sample_count });
          return (
            <span key={day.day_start} title={label} className="flex h-full min-w-0 flex-1 items-end">
              <span
                className={cn(
                  "w-full rounded-t-sm",
                  height === null || day.average_score === null || day.average_score === undefined
                    ? "h-0.5 bg-line"
                    : BAR_TONES[scoreTone(day.average_score) as keyof typeof BAR_TONES] ?? "bg-accent-solid",
                )}
                style={height === null ? undefined : { height: `${height}%` }}
              />
            </span>
          );
        })}
      </div>
      <details className="mt-3 text-sm">
        <summary className="cursor-pointer text-accent hover:underline">{t("quality.admin.showTable")}</summary>
        <div className="mt-2 max-h-64 overflow-auto rounded-lg border border-line">
          <Table caption={t("quality.admin.trendLabel")}>
            <THead>
              <Tr>
                <Th>{t("quality.admin.day")}</Th>
                <Th align="right">{t("quality.admin.count")}</Th>
                <Th align="right">{t("quality.admin.score")}</Th>
              </Tr>
            </THead>
            <TBody>
              {rows.map((day) => (
                <Tr key={day.day_start}>
                  <Td className="whitespace-nowrap">{dayLabel(day)}</Td>
                  <Td align="right" className="tabular-nums">
                    {formatNumber(day.sample_count, locale)}
                  </Td>
                  <Td align="right" className="tabular-nums">
                    {day.average_score !== null && day.average_score !== undefined ? formatScore(day.average_score, locale) : "—"}
                  </Td>
                </Tr>
              ))}
            </TBody>
          </Table>
        </div>
      </details>
    </div>
  );
}
