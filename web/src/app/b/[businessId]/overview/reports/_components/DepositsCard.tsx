"use client";

import Link from "next/link";

import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { hasDepositActivity, noShowLine, type DepositReport, type NoShowRateView } from "@/components/deposits/depositModel";
import { useDepositReport } from "@/components/deposits/useDeposits";
import { IconCard } from "@/components/icons";
import { formatPercent } from "@/components/insights/numbers";
import { Card, ErrorState, LoadingRegion, SkeletonText } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { formatNumber } from "@/lib/format";
import { businessPath } from "@/lib/navigation";

/**
 * Reports → Deposits (owners): the last 30 days of deposits asked, paid,
 * waiting and let go, the money collected and still to return, and how
 * often guests did not come with a paid deposit and without one, and
 * before deposits went on and since. A group with too few finished
 * visits says so instead of showing a share.
 */
export function DepositsCard() {
  const { t } = useI18n();
  const { business } = useBusiness();
  const report = useDepositReport();
  const view = report.data;

  return (
    <Card
      aria-label={t("deposits.report.title")}
      title={
        <span className="flex items-center gap-2">
          <IconCard className="size-4 text-accent" aria-hidden />
          {t("deposits.report.title")}
        </span>
      }
      description={t("deposits.report.description")}
    >
      {report.error && !view ? (
        <ErrorState error={report.error} onRetry={report.reload} className="py-4" />
      ) : !view ? (
        <LoadingRegion label={t("deposits.report.loading")}>
          <SkeletonText lines={4} />
        </LoadingRegion>
      ) : !hasDepositActivity(view) ? (
        <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-ink-muted">
          <span>{t("deposits.report.off")}</span>
          <Link
            href={businessPath(business.id, "settings/deposits")}
            className="font-medium text-accent underline underline-offset-2 hover:no-underline"
          >
            {t("deposits.report.openSettings")}
          </Link>
        </p>
      ) : (
        <DepositFigures view={view} />
      )}
    </Card>
  );
}

function DepositFigures({ view }: { view: DepositReport }) {
  const { t, locale } = useI18n();
  const format = useBusinessFormat();
  const counts: { key: MessageKey; value: number }[] = [
    { key: "deposits.report.requested", value: view.requested_count },
    { key: "deposits.report.paid", value: view.paid_count },
    { key: "deposits.report.awaiting", value: view.awaiting_count },
    { key: "deposits.report.expired", value: view.expired_count },
  ];
  const money = view.money ?? [];

  return (
    <div className="space-y-5">
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {counts.map((count) => (
          <div key={count.key} className="rounded-xl bg-surface-muted px-3 py-2.5">
            <dt className="text-xs text-ink-muted">{t(count.key)}</dt>
            <dd className="text-xl font-semibold text-ink tabular-nums">{formatNumber(count.value, locale)}</dd>
          </div>
        ))}
      </dl>
      {money.length > 0 ? (
        <dl className="grid gap-3 sm:grid-cols-2">
          {money.map((line) => (
            <div key={line.currency_code} className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-t border-line pt-3">
              <dt className="text-sm text-ink-muted">{t("deposits.report.collected")}</dt>
              <dd className="font-semibold text-ink tabular-nums">{format.money(line.collected_minor, line.currency_code)}</dd>
              {line.refund_due_minor > 0 ? (
                <>
                  <dt className="text-sm text-ink-muted">{t("deposits.report.refundDue")}</dt>
                  <dd className="font-medium text-warning tabular-nums">{format.money(line.refund_due_minor, line.currency_code)}</dd>
                </>
              ) : null}
            </div>
          ))}
        </dl>
      ) : null}
      <dl className="grid gap-3 sm:grid-cols-2">
        <NoShowFigure label={t("deposits.report.noShowWith")} rate={view.with_deposit} minSample={view.min_sample} />
        <NoShowFigure label={t("deposits.report.noShowWithout")} rate={view.without_deposit} minSample={view.min_sample} />
      </dl>
      {view.enabled_at && view.before_deposits && view.since_deposits ? (
        <section aria-label={t("deposits.report.enabledSince", { date: format.date(view.enabled_at) })} className="space-y-2">
          <p className="text-xs text-ink-subtle">{t("deposits.report.enabledSince", { date: format.date(view.enabled_at) })}</p>
          <dl className="grid gap-3 sm:grid-cols-2">
            <NoShowFigure label={t("deposits.report.noShowBefore")} rate={view.before_deposits} minSample={view.min_sample} />
            <NoShowFigure label={t("deposits.report.noShowSince")} rate={view.since_deposits} minSample={view.min_sample} />
          </dl>
        </section>
      ) : null}
    </div>
  );
}

function NoShowFigure({ label, rate, minSample }: { label: string; rate: NoShowRateView; minSample: number }) {
  const { t, locale } = useI18n();
  const line = noShowLine(rate, minSample);
  return (
    <div className="rounded-xl border border-line px-3 py-2.5">
      <dt className="text-sm text-ink-muted">{label}</dt>
      {line.kind === "rate" ? (
        <dd className="space-y-0.5">
          <span className="block text-xl font-semibold text-ink tabular-nums">{formatPercent(line.percent, locale)}</span>
          <span className="block text-xs text-ink-subtle">
            {t("deposits.report.noShowCounts", {
              noShows: formatNumber(line.noShows, locale),
              finished: formatNumber(line.finished, locale),
            })}
          </span>
        </dd>
      ) : (
        <dd className="text-sm text-ink-subtle">
          {t("deposits.report.notEnoughData", {
            finished: formatNumber(line.finished, locale),
            min: formatNumber(line.min, locale),
          })}
        </dd>
      )}
    </div>
  );
}
