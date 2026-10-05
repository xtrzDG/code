"use client";

import { AnimatedNumber } from "@/components/motion";
import { useI18n } from "@/i18n/client";
import { numberFormat } from "@/lib/intl/formatters";
import type { RoiResult as Result } from "@/lib/publicSite/roi";
import type { RoiPlan } from "@/lib/publicSite/roiOptions";

/** Whole units of the plan's currency: "₾ 1 240", "€576". */
export function wholeMoney(amount: number, currency: string, locale: string): string {
  return numberFormat(locale, { style: "currency", currency, minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(
    Math.round(amount),
  );
}

/**
 * What the visitor's numbers are worth a month against the plan: the money,
 * the bookings behind it, the multiple of the price (or that it stays below
 * it) and how many bookings pay for the plan. Read out when it changes.
 */
export function RoiResult({ result, plan, hasCheck }: { result: Result; plan: RoiPlan; hasCheck: boolean }) {
  const { t, tp, locale } = useI18n();
  const money = (amount: number) => wholeMoney(amount, plan.currency, locale);
  const price = money(plan.monthly);
  const bookings = Math.round(result.bookings);
  const decimal = numberFormat(locale, { maximumFractionDigits: 1 });

  return (
    <div
      className="flex h-full flex-col justify-between gap-6 rounded-2xl border border-accent/30 bg-accent-soft/40 p-6 sm:p-7"
      aria-live="polite"
      data-testid="roi-result"
    >
      <div className="space-y-2">
        <p className="text-sm text-ink-muted">{t("roi.resultLabel")}</p>
        {hasCheck ? (
          <p className="text-4xl font-semibold tracking-tight text-ink tabular-nums sm:text-5xl">
            <AnimatedNumber value={Math.round(result.monthlyValue)} format={money} durationMs={500} />
          </p>
        ) : (
          <p className="text-base text-ink">{t("roi.noCheck")}</p>
        )}
        <p className="text-sm text-ink-muted">
          {bookings >= 1 ? tp("roi.bookings", bookings) : result.bookings > 0 ? t("roi.bookingsUnderOne") : tp("roi.bookings", 0)}
        </p>
      </div>
      {hasCheck ? (
        <ul className="space-y-2 border-t border-line pt-4 text-sm text-ink">
          <li>
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
