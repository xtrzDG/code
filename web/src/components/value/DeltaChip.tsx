"use client";

import { formatPercent } from "@/components/insights/numbers";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { formatNumber } from "@/lib/format";

import { changeLabel, changeOf, sentimentOf, type Polarity, type Sentiment } from "./valueModel";

const SENTIMENT_STYLES: Record<Sentiment, string> = {
  positive: "border-success/30 bg-success-soft text-success",
  negative: "border-danger/30 bg-danger-soft text-danger",
  neutral: "border-line bg-surface-muted text-ink-muted",
};

/**
 * How a number moved since the period before, as a small chip: an arrow
 * and the change ("▲ 12%"), coloured by whether it is good news, and for
 * screen readers (and as a tooltip) the whole sentence: "Up 12% vs the
 * previous 30 days". Nothing when both periods are zero.
 */
export function DeltaChip({
  current,
  previous,
  days,
  polarity = "more-is-better",
  formatValue,
  className,
}: {
  current: number;
  previous: number;
  /** Length of the compared periods, in days (1 reads "vs the day before"). */
  days: number;
  polarity?: Polarity;
  /** How a difference from none reads ("+GEL 1,920" for money); plain numbers by default. */
  formatValue?: (value: number) => string;
  className?: string;
}) {
  const { t, tp, locale } = useI18n();
  const change = changeOf(current, previous);
  if (change === null) {
    return null;
  }
  const visible = changeLabel(
    change,
    formatValue ?? ((value) => formatNumber(value, locale)),
    (percent) => formatPercent(percent, locale),
  );
  const amount = visible.replace(/^[▲▼=]\s*\+?/, "");
  const against = days === 1 ? t("value.delta.againstDay") : tp("value.delta.againstDays", days);
  const sentence =
    change.direction === "same"
      ? t("value.delta.same", { against })
      : t(change.direction === "up" ? "value.delta.up" : "value.delta.down", { change: amount, against });
  return (
    <span
      title={sentence}
      className={cn(
        // relative: the screen-reader text stays inside (a scrolling table must not widen the page).
        "relative inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-semibold whitespace-nowrap tabular-nums",
        SENTIMENT_STYLES[sentimentOf(change, polarity)],
        className,
      )}
    >
      <span aria-hidden>{visible}</span>
      <span className="sr-only">{sentence}</span>
    </span>
  );
}
