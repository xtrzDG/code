"use client";

import { AnimatedNumber } from "@/components/siteMotion";
import { useI18n } from "@/i18n/client";
import { numberFormat } from "@/lib/intl/formatters";
import type { RoiResult as Result } from "@/lib/publicSite/roi";
import type { RoiPlan } from "@/lib/publicSite/roiOptions";

/** Whole units of the plan's currency: "₾ 1 240", "€576". */
function wholeMoney(amount: number, currency: string, locale: string): string {
  return numberFormat(locale, { style: "currency", currency, minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(
    Math.round(amount),
  );
}

/**
 * What the visitor's numbers are worth a month against the plan: the money,
 * how it adds up (answers after hours, the bookings among them, the
 * check), the multiple of the price (or that it stays below it) and how
 * many bookings pay for the plan. Read out when it changes.
 */
export function RoiResult({
  result,
  plan,
  averageCheck,
}: {
  result: Result;
  plan: RoiPlan;
  averageCheck: number;
}) {
  const { t, tp, locale } = useI18n();
  const money = (amount: number) => wholeMoney(amount, plan.currency, locale);
  const price = money(plan.monthly);
  const hasCheck = averageCheck > 0;
  const bookings = Math.round(result.bookings);
  const whole = numberFormat(locale, { maximumFractionDigits: 0 });
  const decimal = numberFormat(locale, { maximumFractionDigits: 1 });
  const rows: [string, string][] = [
    [t("roi.breakdown.answered"), whole.format(result.answeredRequests)],
    [t("roi.breakdown.bookings"), decimal.format(result.bookings)],
    [t("roi.breakdown.check"), hasCheck ? money(averageCheck) : "—"],
  ];

  return (
    <div
      className="flex flex-col gap-6 rounded-2xl border border-accent/30 bg-accent-soft/40 p-6 sm:p-7"
      aria-live="polite"
      data-testid="roi-result"
    >
      <div className="space-y-2">
        <p className="text-sm text-ink-muted">{t("roi.resultLabel")}</p>
        {hasCheck ? (
          <p className="text-4xl font-semibold tracking-tight text-ink tabular-nums sm:text-5xl" data-testid="roi-value">
            <AnimatedNumber value={Math.round(result.monthlyValue)} format={money} durationMs={500} />
          </p>
        ) : (
          <p className="text-base text-ink">{t("roi.noCheck")}</p>
        )}
        <p className="text-sm text-ink-muted">
          {bookings >= 1 ? tp("roi.bookings", bookings) : result.bookings > 0 ? t("roi.bookingsUnderOne") : tp("roi.bookings", 0)}
        </p>
      </div>
      <dl aria-label={t("roi.breakdown.label")} className="space-y-2 border-t border-line pt-4 text-sm">
        {rows.map(([label, value]) => (
          <div key={label} className="flex items-baseline justify-between gap-4">
            <dt className="text-ink-muted">{label}</dt>
            <dd className="shrink-0 font-medium text-ink tabular-nums">{value}</dd>
          </div>
        ))}
      </dl>
      {hasCheck ? (
        <ul className="space-y-2 border-t border-line pt-4 text-sm text-ink">
          <li data-testid="roi-multiple">
            {result.multiple !== null && result.multiple >= 1
              ? t("roi.multiple", { multiple: decimal.format(result.multiple), plan: plan.name, price })
              : t("roi.belowPrice", { plan: plan.name, price })}
          </li>
          {result.breakEvenBookings !== null ? <li className="text-ink-muted">{tp("roi.breakEven", result.breakEvenBookings)}</li> : null}
        </ul>
      ) : null}
    </div>
  );
}
