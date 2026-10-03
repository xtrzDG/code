"use client";

import { AnimatedNumber } from "@/components/motion";
import { DeltaChip } from "@/components/value/DeltaChip";
import { earningCount, formatWholeMoney, savedTime, type ValueTotals } from "@/components/value/valueModel";
import { useI18n } from "@/i18n/client";
import { formatNumber } from "@/lib/format";

/**
 * A period in one glance: the assistant's bookings (or requests) and what
 * they are worth, the conversations after hours and the staff time saved,
 * each with its change against the period before.
 */
export function ReportSummary({
  current,
  previous,
  basis,
  currency,
  days,
}: {
  current: ValueTotals;
  previous: ValueTotals;
  basis: "bookings" | "requests";
  currency: string;
  /** Length of the period, for the change chips. */
  days: number;
}) {
  const { t, tp, locale } = useI18n();
  const number = (value: number) => formatNumber(value, locale);
  const count = earningCount(basis, current);
  const estimate = current.estimated_revenue_minor;
  const saved = savedTime(current.staff_minutes_saved);
  const hasEstimate = estimate !== null && estimate !== undefined;

  return (
    <div className="space-y-3">
      <p className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <span className="text-2xl font-semibold tracking-tight text-ink tabular-nums sm:text-3xl">
          {tp(basis === "requests" ? "reports.summary.requests" : "reports.summary.bookings", count, { count: number(count) })}
        </span>
        {hasEstimate ? (
          <span className="text-xl font-semibold text-accent tabular-nums sm:text-2xl">
            ≈ <AnimatedNumber value={estimate} format={(minor) => formatWholeMoney(minor, currency, locale)} />
          </span>
        ) : null}
        <DeltaChip
          current={hasEstimate ? estimate : count}
          previous={hasEstimate ? (previous.estimated_revenue_minor ?? 0) : earningCount(basis, previous)}
          days={days}
          className="self-center"
        />
      </p>
      <ul className="flex flex-wrap gap-2 text-sm">
        <li className="inline-flex items-center gap-2 rounded-full border border-line bg-surface-muted/60 px-3 py-1">
          <span className="text-ink">
            {tp("value.hero.afterHours", current.after_hours_conversation_count, {
              count: number(current.after_hours_conversation_count),
            })}
          </span>
          <DeltaChip current={current.after_hours_conversation_count} previous={previous.after_hours_conversation_count} days={days} />
        </li>
        <li className="inline-flex items-center gap-2 rounded-full border border-line bg-surface-muted/60 px-3 py-1">
          <span className="text-ink">
            {tp(saved.unit === "hours" ? "value.hero.hoursSaved" : "value.hero.minutesSaved", saved.count, {
              count: number(saved.count),
            })}
          </span>
          <DeltaChip current={current.staff_minutes_saved} previous={previous.staff_minutes_saved} days={days} />
        </li>
        <li className="inline-flex items-center gap-2 rounded-full border border-line bg-surface-muted/60 px-3 py-1">
          <span className="text-ink">
            {tp("value.hero.conversations", current.conversation_count, { count: number(current.conversation_count) })}
          </span>
          <DeltaChip current={current.conversation_count} previous={previous.conversation_count} days={days} />
        </li>
      </ul>
      {hasEstimate ? null : <p className="text-sm text-ink-muted">{t("value.hero.noMoney")}</p>}
    </div>
  );
}
